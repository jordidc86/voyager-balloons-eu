from __future__ import annotations

import csv
import subprocess
import tempfile
from pathlib import Path

from ..config import ROOT
from ..storage import Store
from ..types import AlertSpec, CheckResult


def run(config: dict, store: Store, run_id: int) -> CheckResult:
    del config, store, run_id
    result = CheckResult(job_name="backlinks")
    with tempfile.NamedTemporaryFile(suffix=".csv") as audit_file:
        process = subprocess.run(
            ["node", "scripts/backlink-outreach.js", "audit", "--output", audit_file.name],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )
        if process.returncode != 0:
            raise RuntimeError(process.stderr.strip() or process.stdout.strip() or "Falló la auditoría de backlinks")
        audit_file.seek(0)
        rows = list(csv.DictReader(line.decode("utf-8") for line in audit_file.readlines()))
    live = [row for row in rows if row.get("link_found") == "true"]
    missing_won = [row for row in rows if row.get("status") == "won" and row.get("link_found") != "true"]
    errors = [row for row in rows if row.get("notes", "").startswith("fetch_error")]

    for row in missing_won:
        result.alerts.append(AlertSpec(
            dedupe_key=f"backlinks:lost:{row['domain']}:{row['target_url']}", severity="P1", category="backlinks",
            title=f"Backlink ganado ya no se detecta: {row['domain']}",
            message=f"No aparece el enlace esperado hacia {row['target_url']}.",
            action="Verificar manualmente y contactar al partner solo si el enlace fue retirado de verdad.",
            evidence_url=row.get("url_or_profile"), metadata=row,
        ))
    result.summary = {
        "relationships_checked": len(rows),
        "live_links_or_mentions": len(live),
        "missing_won_links": len(missing_won),
        "fetch_errors": len(errors),
        "alerts": len(result.alerts),
    }
    result.add_metric("relationships_checked", len(rows), source="backlinks")
    result.add_metric("live_links_or_mentions", len(live), source="backlinks")
    return result
