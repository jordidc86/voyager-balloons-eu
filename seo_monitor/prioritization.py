from __future__ import annotations

import json
from dataclasses import dataclass


SEVERITY_BASE = {"P0": 86, "P1": 68, "P2": 42, "P3": 18}
CATEGORY_BONUS = {
    "commerce": 12,
    "tracking": 10,
    "health": 10,
    "deployment": 9,
    "ga4": 8,
    "gsc": 8,
    "technical": 7,
    "indexing": 7,
    "rank": 7,
    "keyword_demand": 6,
    "pagespeed": 5,
    "backlinks": 4,
    "backlink_gap": 4,
    "local_visibility": 4,
    "ai_visibility": 3,
    "competitors": 2,
}


@dataclass(frozen=True)
class PrioritizedAction:
    score: int
    impact: str
    horizon: str
    effort: str
    destination: str
    upside: str
    rationale: str


def _metadata(raw: str | None) -> dict:
    try:
        value = json.loads(raw or "{}")
    except (TypeError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _text(alert) -> str:
    return " ".join([
        alert.title or "",
        alert.message or "",
        alert.action or "",
        alert.evidence_url or "",
    ]).lower()


def _destination(text: str) -> str:
    if "bragança" in text or "braganca" in text or "braganza" in text:
        return "Bragança"
    if "madrid" in text:
        return "Madrid"
    if "segovia" in text:
        return "Segovia"
    return "Global"


def _effort(category: str) -> str:
    if category in {"gsc", "indexing", "health", "deployment", "tracking"}:
        return "bajo"
    if category in {"commerce", "rank", "keyword_demand", "technical", "ga4"}:
        return "medio"
    return "alto" if category in {"backlinks", "backlink_gap", "local_visibility"} else "medio"


def _impact(category: str, text: str) -> str:
    if category in {"commerce", "health", "deployment", "tracking"} or any(
        word in text for word in ("carrito", "checkout", "compra", "pago")
    ):
        return "protección de ingresos"
    if category in {"gsc", "ga4", "rank", "keyword_demand", "indexing", "pagespeed"}:
        return "crecimiento de reservas"
    if category in {"backlinks", "backlink_gap", "local_visibility", "ai_visibility"}:
        return "autoridad y descubrimiento"
    return "salud orgánica"


def _upside(category: str, metadata: dict) -> tuple[str, int]:
    queries = metadata.get("queries") or []
    click_gap = sum(float(item.get("estimated_click_gap") or 0) for item in queries)
    if click_gap > 0:
        return (
            f"hasta {click_gap:.1f} clics orgánicos adicionales por periodo, según brecha CTR",
            min(10, round(click_gap / 2)),
        )

    opportunities = metadata.get("opportunities") or []
    search_volume = sum(float(item.get("search_volume") or 0) for item in opportunities)
    if search_volume > 0:
        return (
            f"{search_volume:.0f} búsquedas mensuales detectadas en oportunidades fuera del top 10",
            min(8, round(search_volume / 250)),
        )

    if category == "commerce":
        return "riesgo directo de abandono o pérdida de una compra", 7
    if category in {"health", "deployment", "tracking"}:
        return "protege la disponibilidad o la atribución de reservas", 5
    if category == "indexing":
        return "permite que una landing estratégica pueda competir en Google", 4
    if category == "pagespeed":
        return "reduce fricción, especialmente en sesiones móviles de compra", 3
    return "impacto potencial; requiere validar con tendencia y conversiones", 0


def prioritize_alert(alert) -> PrioritizedAction:
    metadata = _metadata(alert.metadata_json)
    text = _text(alert)
    category = alert.category or ""
    upside, evidence_bonus = _upside(category, metadata)
    score = SEVERITY_BASE.get(alert.severity, 10) + CATEGORY_BONUS.get(category, 0) + evidence_bonus

    commercial_terms = (
        "reserva", "producto", "carrito", "checkout", "compra", "comfort", "regalo",
        "vuelo en globo", "balloon ride", "passeio de balão", "passeio de balao",
    )
    if any(term in text for term in commercial_terms):
        score += 4
    if "shop.voyagerballoons.eu" in text:
        score += 3
    score = max(0, min(100, score))

    horizon = {
        "P0": "hoy",
        "P1": "próximos 7 días",
        "P2": "próximos 30 días",
        "P3": "vigilar",
    }.get(alert.severity, "vigilar")
    impact = _impact(category, text)
    rationale = (
        f"{alert.severity} en {category or 'monitorización'}; prioridad ajustada por "
        f"{impact} y evidencia disponible. El score ordena trabajo, no estima ingresos garantizados."
    )
    return PrioritizedAction(
        score=score,
        impact=impact,
        horizon=horizon,
        effort=_effort(category),
        destination=_destination(text),
        upside=upside,
        rationale=rationale,
    )


def prioritized_alerts(alerts: list) -> list[tuple[object, PrioritizedAction]]:
    actions = [(alert, prioritize_alert(alert)) for alert in alerts]
    return sorted(actions, key=lambda item: (-item[1].score, item[0].title))
