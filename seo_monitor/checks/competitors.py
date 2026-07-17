from __future__ import annotations

import hashlib
import json
import re
import time

import requests
from bs4 import BeautifulSoup

from ..storage import Store
from ..types import AlertSpec, CheckResult


PRICE_RE = re.compile(r"(?:€\s?\d{2,4}|\d{2,4}(?:[.,]\d{1,2})?\s?€)")


def inspect(url: str, timeout: float) -> dict:
    started = time.perf_counter()
    response = requests.get(
        url,
        timeout=timeout,
        allow_redirects=True,
        headers={"User-Agent": "Mozilla/5.0 (compatible; VoyagerSEOCompetitorMonitor/0.1)"},
    )
    soup = BeautifulSoup(response.text, "html.parser")
    for node in soup(["script", "style", "noscript", "svg"]):
        node.decompose()
    text = " ".join(soup.get_text(" ", strip=True).split())
    title = soup.title.get_text(" ", strip=True) if soup.title else None
    h1 = soup.find("h1").get_text(" ", strip=True) if soup.find("h1") else None
    prices = sorted(set(PRICE_RE.findall(text)))
    stable_text = re.sub(r"\b\d{1,2}[:/]\d{1,2}(?:[:/]\d{2,4})?\b", "", text)
    return {
        "url": url,
        "status_code": response.status_code,
        "final_url": response.url,
        "elapsed_ms": round((time.perf_counter() - started) * 1000, 1),
        "title": title,
        "h1": h1,
        "prices": prices,
        "robots": None,
        "canonical": None,
        "content_hash": hashlib.sha256(stable_text.encode("utf-8")).hexdigest(),
        "text_length": len(text),
    }


def run(config: dict, store: Store, run_id: int) -> CheckResult:
    result = CheckResult(job_name="competitors")
    timeout = float(config["thresholds"].get("health_timeout_seconds", 25))
    changes = 0
    failures = 0

    for competitor in config.get("competitors", []):
        url = competitor["url"]
        previous = store.latest_page_snapshot("competitors", url)
        try:
            snapshot = inspect(url, timeout)
        except Exception as exc:
            failures += 1
            result.alerts.append(AlertSpec(
                dedupe_key=f"competitors:unavailable:{competitor['domain']}", severity="P3", category="competitors",
                title=f"No se pudo revisar {competitor['name']}", message=str(exc),
                action="Reintentar en el siguiente ciclo; no interpretar un bloqueo anti-bot como caída real.", evidence_url=url,
            ))
            continue

        previous_payload = json.loads(previous.payload_json) if previous else None
        store.add_page_snapshot(run_id, "competitors", snapshot)
        if previous_payload and snapshot["status_code"] < 400:
            changed_fields = []
            for field in ("title", "h1", "prices"):
                if previous_payload.get(field) != snapshot.get(field):
                    changed_fields.append(field)
            if changed_fields:
                changes += 1
                result.alerts.append(AlertSpec(
                    dedupe_key=f"competitors:change:{competitor['domain']}", severity="P2", category="competitors",
                    title=f"Cambio comercial en {competitor['name']}",
                    message=f"Han cambiado: {', '.join(changed_fields)}. Precios visibles: {', '.join(snapshot['prices']) or 'ninguno'}.",
                    action="Comparar el nuevo mensaje/oferta con nuestras landings antes de decidir si debemos responder.",
                    evidence_url=url, metadata={"changed_fields": changed_fields, "prices": snapshot["prices"]},
                ))
        result.add_metric("competitor_status", snapshot["status_code"], source="competitors", dimensions={"domain": competitor["domain"]})

    result.summary = {
        "competitors_configured": len(config.get("competitors", [])),
        "changes": changes,
        "failures": failures,
        "alerts": len(result.alerts),
    }
    return result
