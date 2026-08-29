from __future__ import annotations

import time

import requests
from bs4 import BeautifulSoup

from ..storage import Store
from ..types import AlertSpec, CheckResult


USER_AGENT = "VoyagerSEOCheckoutTest/1.0 (+https://www.voyagerballoons.eu/)"


def _alert(probe: dict, stage: str, message: str, metadata: dict | None = None) -> AlertSpec:
    return AlertSpec(
        dedupe_key=f"commerce:{stage}:{probe['name'].lower().replace(' ', '-')}",
        severity=str(probe.get("severity") or "P0"),
        category="commerce",
        title=f"Flujo comercial no disponible: {probe['name']}",
        message=message,
        action="Revisar el servicio activo, su despliegue y la conexión con el Dashboard antes de enviar tráfico de pago.",
        evidence_url=probe["url"],
        metadata=metadata or {},
    )


def _page_probe(probe: dict, response: requests.Response) -> list[AlertSpec]:
    alerts: list[AlertSpec] = []
    soup = BeautifulSoup(response.text, "html.parser")
    visible = soup.get_text(" ", strip=True).casefold()
    missing = [
        text for text in probe.get("expected_text", [])
        if str(text).strip().casefold() not in visible
    ]
    if missing:
        alerts.append(_alert(
            probe,
            "content",
            f"La página carga, pero no contiene las señales esperadas: {', '.join(map(str, missing))}.",
            {"missing": missing, "final_url": response.url},
        ))

    expected_robots = str(probe.get("expected_robots") or "").casefold()
    if expected_robots:
        robots = soup.find("meta", attrs={"name": lambda value: value and value.casefold() == "robots"})
        content = str(robots.get("content") if robots else "").casefold()
        if expected_robots not in content:
            alerts.append(_alert(
                probe,
                "robots",
                f"La página no declara la política robots esperada ({expected_robots}).",
                {"robots": content, "final_url": response.url},
            ))
    return alerts


def _json_probe(probe: dict, response: requests.Response) -> list[AlertSpec]:
    try:
        payload = response.json()
    except ValueError:
        return [_alert(probe, "health-json", "El endpoint de salud no devuelve JSON válido.")]
    missing = {
        key: value for key, value in probe.get("expected_json", {}).items()
        if payload.get(key) != value
    }
    if missing:
        return [_alert(
            probe,
            "health-contract",
            "El endpoint responde, pero no confirma el modo de producción esperado.",
            {"expected": probe.get("expected_json", {}), "received": payload},
        )]
    return []


def test_probe(probe: dict, timeout: float) -> tuple[dict, list[AlertSpec]]:
    started = time.perf_counter()
    response = requests.get(
        probe["url"],
        timeout=timeout,
        allow_redirects=True,
        headers={"User-Agent": USER_AGENT, "Accept-Language": "es,en,pt;q=0.8"},
    )
    if response.status_code >= 400:
        return {
            "probe": probe["name"],
            "status": response.status_code,
            "flow_ok": False,
        }, [_alert(probe, "http", f"La URL devuelve HTTP {response.status_code}.")]

    alerts = _json_probe(probe, response) if probe.get("kind") == "json" else _page_probe(probe, response)
    return {
        "probe": probe["name"],
        "status": response.status_code,
        "final_url": response.url,
        "flow_ok": not alerts,
        "elapsed_ms": round((time.perf_counter() - started) * 1000, 1),
    }, alerts


def run(config: dict, store: Store, run_id: int) -> CheckResult:
    del store, run_id
    result = CheckResult(job_name="commerce")
    result.resolution_prefixes = ["commerce:"]
    timeout = float(config["thresholds"].get("health_timeout_seconds", 25))
    outcomes = []
    for probe in config.get("commerce_probes", []):
        try:
            outcome, alerts = test_probe(probe, timeout)
        except Exception as exc:
            outcome = {"probe": probe["name"], "error": str(exc), "flow_ok": False}
            alerts = [_alert(probe, "exception", f"La prueba sintética terminó con error: {exc}")]
        outcomes.append(outcome)
        result.alerts.extend(alerts)
        result.add_metric("flow_ok", int(not alerts), source="commerce", dimensions={"probe": probe["name"]})
        if "elapsed_ms" in outcome:
            result.add_metric("flow_elapsed_ms", outcome["elapsed_ms"], source="commerce", dimensions={"probe": probe["name"]})
    result.summary = {
        "probes_tested": len(outcomes),
        "successful_flows": sum(1 for outcome in outcomes if outcome.get("flow_ok")),
        "alerts": len(result.alerts),
        "outcomes": outcomes,
    }
    return result
