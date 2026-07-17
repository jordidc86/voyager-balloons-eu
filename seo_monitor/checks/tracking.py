from __future__ import annotations

from html.parser import HTMLParser
import requests
from urllib.parse import urlsplit

from ..storage import Store
from ..types import AlertSpec, CheckResult


class _ScriptParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.scripts: list[dict[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "script":
            self.scripts.append({name: value or "" for name, value in attrs})


def _script_attributes(html: str) -> list[dict[str, str]]:
    parser = _ScriptParser()
    parser.feed(html)
    return parser.scripts


def _fetch(url: str) -> str:
    response = requests.get(url, timeout=30, headers={"User-Agent": "VoyagerSEO-Monitor/1.0"})
    response.raise_for_status()
    return response.text


def _audit(main_html: str, tracking_js: str, shop_html: str, tracking_config: dict) -> list[dict]:
    tag_id = tracking_config["google_tag_id"]
    ads_id = tracking_config["google_ads_id"]
    main_domain = tracking_config["main_domain"]
    shop_domain = tracking_config["shop_domain"]
    script_url = tracking_config["main_script_url"]
    script_path = urlsplit(script_url).path
    shop_scripts = _script_attributes(shop_html)
    woo_provider = next(
        (script for script in shop_scripts if script.get("id") == "googlesitekit-events-provider-woocommerce-js"),
        None,
    )
    return [
        {
            "key": "main-script",
            "ok": script_url in main_html or script_path in main_html,
            "severity": "P1",
            "message": "La web principal ya no carga el script de medición propio.",
        },
        {
            "key": "main-tag",
            "ok": tag_id in tracking_js and ads_id in tracking_js,
            "severity": "P1",
            "message": "El script principal no contiene las etiquetas de Google esperadas.",
        },
        {
            "key": "main-linker",
            "ok": all(token in tracking_js for token in (main_domain, shop_domain, "accept_incoming", "decorate_forms")),
            "severity": "P1",
            "message": "La configuración cross-domain de la web principal está incompleta.",
        },
        {
            "key": "shop-tag",
            "ok": tag_id in shop_html and ads_id in shop_html,
            "severity": "P1",
            "message": "La tienda no contiene las mismas etiquetas de Google que la web principal.",
        },
        {
            "key": "shop-linker",
            "ok": all(token in shop_html for token in (main_domain, shop_domain, "accept_incoming", "decorate_forms")),
            "severity": "P1",
            "message": "La tienda ha perdido parte de su configuración cross-domain.",
        },
        {
            "key": "woocommerce-events",
            "ok": "eventsToTrack" in shop_html and "add_to_cart" in shop_html and "purchase" in shop_html,
            "severity": "P1",
            "message": "Site Kit/WooCommerce ya no declara los eventos add_to_cart y purchase.",
        },
        {
            "key": "woocommerce-listener-immediate",
            "ok": bool(woo_provider) and woo_provider.get("type") != "rocketlazyloadscript",
            "severity": "P1",
            "message": "WP Rocket vuelve a retrasar el listener de Site Kit que registra los productos añadidos al carrito.",
        },
        {
            "key": "shop-links",
            "ok": shop_domain in main_html,
            "severity": "P0",
            "message": "La web principal ya no contiene enlaces hacia la tienda.",
        },
    ]


def run(config: dict, store: Store, run_id: int) -> CheckResult:
    del store, run_id
    result = CheckResult(job_name="tracking")
    tracking_config = config["tracking"]
    urls = {
        "main": tracking_config["main_url"],
        "script": tracking_config["main_script_url"],
        "shop": tracking_config["shop_url"],
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
        findings = _audit(payloads["main"], payloads["script"], payloads["shop"], tracking_config)
        for finding in findings:
            if finding["ok"]:
                continue
            result.alerts.append(AlertSpec(
                dedupe_key=f"tracking:{finding['key']}",
                severity=finding["severity"],
                category="tracking",
                title="Riesgo en la medición de reservas",
                message=finding["message"],
                action="Restaurar la etiqueta y validar de nuevo la navegación web → tienda, add_to_cart y purchase antes de interpretar GA4.",
                evidence_url=tracking_config["main_url"] if finding["key"].startswith("main") else tracking_config["shop_url"],
                metadata={"check": finding["key"]},
            ))
    if failures:
        result.alerts.append(AlertSpec(
            dedupe_key="tracking:fetch-failures",
            severity="P1",
            category="tracking",
            title="No se pudo verificar la medición de conversiones",
            message=f"Fallaron {len(failures)} de {len(urls)} recursos necesarios para comprobar Analytics.",
            action="Comprobar disponibilidad y repetir la prueba antes de confiar en los datos de conversión.",
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
