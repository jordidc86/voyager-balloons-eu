from __future__ import annotations

import hashlib
import json

from ..config import Settings
from ..google_auth import authorized_session
from ..storage import Store
from ..types import AlertSpec, CheckResult


SCOPE = "https://www.googleapis.com/auth/webmasters.readonly"
ENDPOINT = "https://searchconsole.googleapis.com/v1/urlInspection/index:inspect"


def _inspect(session, property_name: str, url: str) -> dict:
    response = session.post(
        ENDPOINT,
        json={"inspectionUrl": url, "siteUrl": property_name, "languageCode": "es-ES"},
        timeout=45,
    )
    response.raise_for_status()
    return response.json().get("inspectionResult", {})


def run(config: dict, store: Store, run_id: int, settings: Settings) -> CheckResult:
    result = CheckResult(job_name="indexing")
    if not settings.google_service_account_json:
        result.status = "skipped"
        result.summary = {"reason": "GOOGLE_SERVICE_ACCOUNT_JSON no configurado"}
        return result

    session = authorized_session(settings.google_service_account_json, [SCOPE])
    pages = [page for page in config["strategic_pages"] if not page.get("allow_noindex")]
    indexed = 0
    failures = []

    for page in pages:
        try:
            inspection = _inspect(session, settings.gsc_property, page["url"])
        except Exception as exc:
            failures.append({"url": page["url"], "error": str(exc)})
            continue

        status = inspection.get("indexStatusResult", {})
        verdict = status.get("verdict", "VERDICT_UNSPECIFIED")
        coverage = status.get("coverageState")
        indexing_state = status.get("indexingState")
        robots_state = status.get("robotsTxtState")
        fetch_state = status.get("pageFetchState")
        google_canonical = status.get("googleCanonical")
        user_canonical = status.get("userCanonical")
        is_indexed = verdict == "PASS"
        indexed += int(is_indexed)
        content_hash = hashlib.sha256(
            json.dumps(status, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest()
        store.add_page_snapshot(run_id, "indexing", {
            "url": page["url"],
            "status_code": 200,
            "final_url": google_canonical,
            "title": coverage,
            "canonical": user_canonical,
            "robots": f"{robots_state}/{indexing_state}",
            "content_hash": content_hash,
            "verdict": verdict,
            "coverage_state": coverage,
            "indexing_state": indexing_state,
            "robots_txt_state": robots_state,
            "page_fetch_state": fetch_state,
            "last_crawl_time": status.get("lastCrawlTime"),
            "referring_urls": status.get("referringUrls", []),
            "sitemap": status.get("sitemap", []),
        })
        result.add_metric(
            "indexed",
            int(is_indexed),
            source="indexing",
            dimensions={"url": page["url"], "coverage": coverage or "unknown"},
        )

        explicitly_blocked = verdict == "FAIL" or indexing_state not in {
            None,
            "INDEXING_ALLOWED",
            "INDEXING_STATE_UNSPECIFIED",
        }
        if explicitly_blocked:
            result.alerts.append(AlertSpec(
                dedupe_key=f"indexing:not-indexed:{page['url']}",
                severity=page.get("severity", "P1"),
                category="indexing",
                title=f"URL estratégica no indexable: {page['name']}",
                message=f"Search Console devuelve {coverage or verdict}; indexación={indexing_state}, rastreo={robots_state}, obtención={fetch_state}.",
                action="Comprobar respuesta publicada, canonical, robots, sitemap y contenido; corregir la causa antes de solicitar una nueva indexación.",
                evidence_url=page["url"],
                metadata=status,
            ))
        elif verdict in {"NEUTRAL", "VERDICT_UNSPECIFIED"}:
            result.alerts.append(AlertSpec(
                dedupe_key=f"indexing:neutral:{page['url']}",
                severity="P2",
                category="indexing",
                title=f"Indexación pendiente o indeterminada: {page['name']}",
                message=f"Search Console no confirma indexación: {coverage or verdict}.",
                action="Revisar descubrimiento mediante sitemap y enlaces internos; observar el siguiente ciclo antes de escalar.",
                evidence_url=page["url"],
                metadata=status,
            ))
        if google_canonical and page.get("canonical") and google_canonical.rstrip("/") != page["canonical"].rstrip("/"):
            result.alerts.append(AlertSpec(
                dedupe_key=f"indexing:google-canonical:{page['url']}",
                severity="P1",
                category="indexing",
                title=f"Google eligió otro canonical: {page['name']}",
                message=f"Declarado: {page['canonical']}. Elegido por Google: {google_canonical}.",
                action="Comparar contenido duplicado, enlaces internos, redirecciones, hreflang y sitemap para consolidar la URL estratégica.",
                evidence_url=page["url"],
                metadata=status,
            ))

    if failures:
        result.alerts.append(AlertSpec(
            dedupe_key="indexing:inspection-failures",
            severity="P1",
            category="indexing",
            title="Search Console no inspeccionó todas las URLs",
            message=f"Fallaron {len(failures)} de {len(pages)} inspecciones automáticas.",
            action="Revisar permisos de la cuenta de servicio, propiedad, cuota y respuesta de la API.",
            metadata={"failures": failures[:20]},
        ))

    result.summary = {
        "pages": len(pages),
        "indexed": indexed,
        "failures": len(failures),
        "alerts": len(result.alerts),
    }
    result.add_metric("pages", len(pages), source="indexing")
    result.add_metric("indexed", indexed, source="indexing")
    return result
