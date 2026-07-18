from __future__ import annotations

import hashlib
import re
import time
from urllib.parse import urlsplit, urlunsplit

import requests
from bs4 import BeautifulSoup

from ..storage import Store
from ..types import AlertSpec, CheckResult


USER_AGENT = "VoyagerSEOIntelligence/0.1 (+https://www.voyagerballoons.eu/)"


def normalize_url(url: str | None) -> str | None:
    if not url:
        return None
    parsed = urlsplit(url.strip())
    path = parsed.path or "/"
    if path != "/":
        path = path.rstrip("/")
    return urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), path, "", ""))


def inspect_page(page: dict, timeout: float) -> dict:
    started = time.perf_counter()
    try:
        response = requests.get(
            page["url"],
            timeout=timeout,
            allow_redirects=True,
            headers={"User-Agent": USER_AGENT, "Accept-Language": "es,en;q=0.8,pt;q=0.7"},
        )
        elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
        content_type = response.headers.get("content-type", "").lower()
        soup = BeautifulSoup(response.text, "html.parser") if "html" in content_type else None
        title = soup.title.get_text(" ", strip=True) if soup and soup.title else None
        canonical_node = soup.find("link", rel=lambda value: value and "canonical" in value) if soup else None
        canonical = canonical_node.get("href", "").strip() if canonical_node else None
        robots_node = soup.find("meta", attrs={"name": re.compile(r"^robots$", re.I)}) if soup else None
        robots = robots_node.get("content", "").strip() if robots_node else None
        h1_count = len(soup.find_all("h1")) if soup else 0
        visible_text = soup.get_text(" ", strip=True) if soup else ""
        content_hash = hashlib.sha256(response.content).hexdigest()
        return {
            "url": page["url"],
            "status_code": response.status_code,
            "final_url": response.url,
            "redirects": len(response.history),
            "elapsed_ms": elapsed_ms,
            "content_type": content_type,
            "title": title,
            "canonical": canonical,
            "robots": robots,
            "h1_count": h1_count,
            "visible_text": visible_text,
            "content_hash": content_hash,
            "error": None,
        }
    except Exception as exc:
        return {
            "url": page["url"],
            "status_code": None,
            "final_url": None,
            "redirects": 0,
            "elapsed_ms": round((time.perf_counter() - started) * 1000, 1),
            "content_type": None,
            "title": None,
            "canonical": None,
            "robots": None,
            "h1_count": 0,
            "visible_text": "",
            "content_hash": None,
            "error": str(exc),
        }


def run(config: dict, store: Store, run_id: int) -> CheckResult:
    result = CheckResult(job_name="health")
    timeout = float(config["thresholds"].get("health_timeout_seconds", 25))
    slow_ms = float(config["thresholds"].get("slow_page_ms", 2500))
    slow_confirmations = int(config["thresholds"].get("slow_page_confirmations", 3))
    checked = []

    for page in config["strategic_pages"]:
        history = store.page_snapshot_history(
            "health",
            page["url"],
            limit=max(0, slow_confirmations - 1),
        )
        snapshot = inspect_page(page, timeout)
        checked.append(snapshot)
        store.add_page_snapshot(run_id, "health", {k: v for k, v in snapshot.items() if k != "visible_text"})
        severity = page.get("severity", "P1")
        key = hashlib.sha1(page["url"].encode()).hexdigest()[:16]
        status = snapshot.get("status_code")

        if status is None or status >= 500:
            result.alerts.append(AlertSpec(
                dedupe_key=f"health:http-critical:{key}", severity="P0", category="health",
                title=f"{page['name']} no responde correctamente",
                message=f"HTTP {status or 'sin respuesta'}: {snapshot.get('error') or 'error de servidor'}",
                action="Comprobar inmediatamente hosting, caché y último despliegue. Pausar campañas si afecta a compra.",
                evidence_url=page["url"], metadata={"status": status},
            ))
            continue
        if status >= 400:
            result.alerts.append(AlertSpec(
                dedupe_key=f"health:http-4xx:{key}", severity=severity, category="health",
                title=f"{page['name']} devuelve HTTP {status}",
                message="Una URL estratégica no está disponible para usuarios o buscadores.",
                action="Restaurar la página o redirigirla a su sustituta y corregir todos los enlaces internos.",
                evidence_url=page["url"], metadata={"status": status},
            ))
            continue
        allowed_final_urls = {normalize_url(url) for url in page.get("allowed_final_urls", [])}
        final_url_allowed = normalize_url(snapshot.get("final_url")) in allowed_final_urls
        if snapshot["redirects"] and not final_url_allowed:
            result.alerts.append(AlertSpec(
                dedupe_key=f"health:redirect:{key}", severity="P1", category="health",
                title=f"{page['name']} redirige antes de cargar",
                message=f"La URL configurada termina en {snapshot['final_url']} tras {snapshot['redirects']} salto(s).",
                action="Actualizar configuración, enlaces internos y campañas para usar directamente la URL final.",
                evidence_url=page["url"], metadata={"final_url": snapshot["final_url"]},
            ))

        expected_canonical = normalize_url(page.get("canonical"))
        actual_canonical = normalize_url(snapshot.get("canonical"))
        if expected_canonical and actual_canonical != expected_canonical:
            result.alerts.append(AlertSpec(
                dedupe_key=f"health:canonical:{key}", severity=severity, category="health",
                title=f"Canonical incorrecto en {page['name']}",
                message=f"Esperado: {expected_canonical}. Encontrado: {actual_canonical or 'ninguno'}.",
                action="Restaurar el canonical autorreferente correcto y revisar el despliegue que lo modificó.",
                evidence_url=page["url"],
            ))

        if not page.get("allow_noindex") and "noindex" in (snapshot.get("robots") or "").lower():
            result.alerts.append(AlertSpec(
                dedupe_key=f"health:noindex:{key}", severity="P0", category="health",
                title=f"Página comercial bloqueada: {page['name']}",
                message="La página estratégica contiene una directiva noindex.",
                action="Eliminar noindex, desplegar y solicitar reindexación tras verificar la URL publicada.",
                evidence_url=page["url"],
            ))

        for required in page.get("required_text", []):
            if required.lower() not in snapshot["visible_text"].lower():
                result.alerts.append(AlertSpec(
                    dedupe_key=f"health:required-text:{key}:{required}", severity=severity, category="health",
                    title=f"Dato comercial ausente en {page['name']}",
                    message=f"No se encuentra el texto obligatorio “{required}” en la página publicada.",
                    action="Revisar precio, idioma, caché y plantilla antes de enviar tráfico a esta URL.",
                    evidence_url=page["url"],
                ))

        slow_streak = 1
        if snapshot["elapsed_ms"] > slow_ms:
            for previous in history:
                if (previous.elapsed_ms or 0) <= slow_ms:
                    break
                slow_streak += 1
        if snapshot["elapsed_ms"] > slow_ms and slow_streak >= slow_confirmations:
            result.alerts.append(AlertSpec(
                dedupe_key=f"health:slow:{key}", severity="P2", category="health",
                title=f"Respuesta lenta en {page['name']}",
                message=(
                    f"La comprobación HTTP tardó {snapshot['elapsed_ms']:.0f} ms; umbral {slow_ms:.0f} ms, "
                    f"superado durante {slow_streak} mediciones consecutivas."
                ),
                action="Confirmar con PageSpeed/CrUX antes de optimizar; revisar TTFB, caché y recursos críticos.",
                evidence_url=page["url"], metadata={"slow_streak": slow_streak, "elapsed_ms": snapshot["elapsed_ms"]},
            ))

    statuses = [item["status_code"] for item in checked]
    result.summary = {
        "pages_checked": len(checked),
        "healthy_2xx": sum(1 for status in statuses if status is not None and 200 <= status < 300),
        "alerts": len(result.alerts),
        "max_elapsed_ms": max((item["elapsed_ms"] for item in checked), default=0),
    }
    result.add_metric("strategic_pages_checked", len(checked))
    result.add_metric("strategic_pages_healthy", result.summary["healthy_2xx"])
    result.add_metric("max_response_ms", result.summary["max_elapsed_ms"])
    return result
