from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


SEVERITY_ORDER = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}


@dataclass(frozen=True)
class AlertSpec:
    dedupe_key: str
    severity: str
    category: str
    title: str
    message: str
    action: str
    evidence_url: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class CheckResult:
    job_name: str
    status: str = "success"
    summary: dict[str, Any] = field(default_factory=dict)
    alerts: list[AlertSpec] = field(default_factory=list)
    metrics: list[dict[str, Any]] = field(default_factory=list)

    def add_metric(
        self,
        name: str,
        value: float,
        source: str | None = None,
        dimensions: dict[str, Any] | None = None,
    ) -> None:
        self.metrics.append({
            "source": source or self.job_name,
            "name": name,
            "value": float(value),
            "dimensions": dimensions or {},
        })
