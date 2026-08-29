from __future__ import annotations

import requests
from urllib.parse import urlsplit

from ..storage import Store
from ..types import AlertSpec, CheckResult


def _fetch(url: str) -> str:
    response = requests.get(url, timeout=30, headers={"User-Agent": "VoyagerSEO-Monitor/1.0"})
    response.raise_for_status()
    return response.text


def _audit(main_html: str, tracking_js: str, store_html: str, tracking_config: dict) -> list[dict]:
    tag_id = tracking_config["google_tag_id"]
    ads_id = tracking_config["google_ads_id"]
    main_domain = tracking_config["main_domain"]
    store_domain = tracking_config["store_domain"]
    script_path = urlsplit(tracking_config["main_script_url"]).path
    return [
        {"key": "main-script", "ok": script_path in main_html, "severity": "P1", "message": "La web principal ya no carga el script de medición propio."},
        {"key": "main-tag", "ok": tag_id in tracking_js and ads_id in tracking_js, "severity": "P1", "message": "El script principal no contiene las etiquetas de Google esperadas."},
        {"key": "main-linker", "ok": all(token in tracking_js for token in (main_domain, store_domain, "accept_incoming", "decorate_forms")), "severity": "P1", "message": "La configuración cross-domain de la web principal está incompleta."},
        {"key": "journey-attribution", "ok": all(token in tracking_js for token in ("vb_landing_path", "vb_referrer_host", "utm_source")), "severity": "P1", "message": "El salto a la tienda ya no conserva la procedencia y landing original."},
        {"key": "store-tag", "ok": tag_id in store_html and ads_id in store_html and "voyager-google-tag-bootstrap" in store_html, "severity": "P1", "message": "La tienda nueva no contiene la misma etiqueta de Google que la web principal."},
        {"key": "store-linker", "ok": all(token in store_html for token in (main_domain, store_domain, "accept_incoming", "decorate_forms")), "severity": "P1", "message": "La tienda nueva ha perdido parte de la configuración cross-domain."},
        {"key": "store-funnel-contract", "ok": all(token in store_html for token in ("voyager-tracking-contract", "add_to_cart", "begin_checkout")), "severity": "P1", "message": "La tienda nueva ya no declara los eventos add_to_cart y begin_checkout."},
        {"key": "store-links", "ok": store_domain in main_html, "severity": "P0", "message": "La web principal ya no contiene enlaces hacia la tienda activa."},
    ]


def run(config: dict, store: Store, run_id: int) -> CheckResult:
    del store, run_id
    result = CheckResult(job_name="tracking")
    result.resolution_prefixes = ["tracking:"]
    tracking_config = config["tracking"]
    urls = {
        "main": tracking_config["main_url"],
        "script": tracking_config["main_script_url"],
        "store": tracking_config["store_url"],
    }
    payloads = {}
    failures = []
    for name, url in urls.items():
        try:
            payloads[name] = _fetch(url)
        except Exception as exc:
            failures.append({"resource": name, "url": url, "error": str(exc)})

    findings = []
    if not failures:
        findings = _audit(payloads["main"], payloads["script"], payloads["store"], tracking_config)
        for finding in findings:
            if finding["ok"]:
                continue
            result.alerts.append(AlertSpec(
                dedupe_key=f"tracking:{finding['key']}",
                severity=finding["severity"],
                category="tracking",
                title="Riesgo en la medición de reservas",
                message=finding["message"],
                action="Restaurar el contrato de medición y validar web → tienda, add_to_cart y begin_checkout sin modificar purchase.",
                evidence_url=tracking_config["main_url"] if finding["key"].startswith(("main", "journey")) else tracking_config["store_url"],
                metadata={"check": finding["key"]},
            ))
    if failures:
        result.alerts.append(AlertSpec(
            dedupe_key="tracking:fetch-failures",
            severity="P1",
            category="tracking",
            title="No se pudo verificar la medición de conversiones",
            message=f"Fallaron {len(failures)} de {len(urls)} recursos necesarios para comprobar Analytics.",
            action="Comprobar disponibilidad y repetir la prueba antes de interpretar datos de conversión.",
            metadata={"failures": failures},
        ))

    passed = sum(1 for finding in findings if finding["ok"])
    result.summary = {
        "checks": len(findings),
        "passed": passed,
        "failed": len(findings) - passed,
        "fetch_failures": len(failures),
        "alerts": len(result.alerts),
    }
    result.add_metric("integrity_checks_passed", passed, source="tracking")
    result.add_metric("integrity_checks_total", len(findings), source="tracking")
    return result
