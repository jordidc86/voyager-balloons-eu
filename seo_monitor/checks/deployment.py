from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import requests

from ..config import ROOT
from ..storage import Store
from ..types import AlertSpec, CheckResult
from .http_health import USER_AGENT


def source_path(source_file: str, root: Path | None = None) -> Path:
    root = root or ROOT
    path = (root / source_file).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError(f"Archivo de despliegue fuera del proyecto: {source_file}") from exc
    if not path.is_file():
        raise FileNotFoundError(f"No existe el archivo de despliegue: {source_file}")
    return path


def expected_hash(source_file: str, root: Path | None = None) -> str:
    return hashlib.sha256(source_path(source_file, root).read_bytes()).hexdigest()


def inspect_remote(probe: dict, timeout: float) -> dict:
    started = time.perf_counter()
    try:
        response = requests.get(
            probe["url"],
            timeout=timeout,
            allow_redirects=True,
            headers={"User-Agent": USER_AGENT, "Cache-Control": "no-cache"},
        )
        return {
            "url": probe["url"],
            "status_code": response.status_code,
            "final_url": response.url,
            "elapsed_ms": round((time.perf_counter() - started) * 1000, 1),
            "content_hash": hashlib.sha256(response.content).hexdigest(),
            "error": None,
        }
    except Exception as exc:
        return {
            "url": probe["url"],
            "status_code": None,
            "final_url": None,
            "elapsed_ms": round((time.perf_counter() - started) * 1000, 1),
            "content_hash": None,
            "error": str(exc),
        }


def _previous_payload(previous) -> dict:
    if not previous or not previous.payload_json:
        return {}
    try:
        return json.loads(previous.payload_json)
    except (TypeError, ValueError):
        return {}


def run(config: dict, store: Store, run_id: int) -> CheckResult:
    result = CheckResult(job_name="deployment")
    deployment_config = config.get("deployment", {})
    probes = deployment_config.get("probes", [])
    timeout = float(config.get("thresholds", {}).get("health_timeout_seconds", 25))
    checked = []
    matches = 0
    mismatches = 0
    confirmed_mismatches = 0
    unavailable = 0

    for probe in probes:
        previous = store.latest_page_snapshot("deployment", probe["url"])
        snapshot = inspect_remote(probe, timeout)
        expected = expected_hash(probe["source_file"])
        snapshot["expected_content_hash"] = expected
        snapshot["source_file"] = probe["source_file"]
        checked.append(snapshot)
        store.add_page_snapshot(run_id, "deployment", snapshot)

        status = snapshot.get("status_code")
        if status is None or not 200 <= status < 300:
            unavailable += 1
            previous_payload = _previous_payload(previous)
            confirmed_unavailable = (
                previous is not None
                and previous_payload.get("expected_content_hash") == expected
                and (previous.status_code is None or not 200 <= previous.status_code < 300)
            )
            if confirmed_unavailable:
                key = hashlib.sha1(probe["url"].encode()).hexdigest()[:16]
                result.alerts.append(AlertSpec(
                    dedupe_key=f"deployment:unavailable:{key}",
                    severity=probe.get("severity", "P1"),
                    category="deployment",
                    title=f"Archivo público no disponible: {probe['name']}",
                    message=(
                        f"La sonda devuelve HTTP {status or 'sin respuesta'} en dos comprobaciones "
                        "consecutivas."
                    ),
                    action="Revisar Netlify, restaurar el archivo y comprobar su respuesta pública.",
                    evidence_url=probe["url"],
                    metadata={"source_file": probe["source_file"], "status": status},
                ))
            continue
        if snapshot.get("content_hash") == expected:
            matches += 1
            continue

        mismatches += 1
        previous_payload = _previous_payload(previous)
        confirmed = (
            previous is not None
            and previous_payload.get("expected_content_hash") == expected
            and previous.content_hash != expected
        )
        if not confirmed:
            continue

        confirmed_mismatches += 1
        key = hashlib.sha1(probe["url"].encode()).hexdigest()[:16]
        result.alerts.append(AlertSpec(
            dedupe_key=f"deployment:stale:{key}",
            severity=probe.get("severity", "P1"),
            category="deployment",
            title=f"Despliegue público desactualizado: {probe['name']}",
            message=(
                f"La versión pública no coincide con {probe['source_file']} en dos comprobaciones "
                "consecutivas. El código puede estar actualizado sin haberse publicado en la web."
            ),
            action=(
                "Revisar el último despliegue de Netlify, sus créditos y el registro de compilación. "
                "Publicar la versión pendiente y verificar que la alerta se resuelva en el siguiente ciclo."
            ),
            evidence_url=probe["url"],
            metadata={
                "source_file": probe["source_file"],
                "expected_hash": expected,
                "public_hash": snapshot.get("content_hash"),
            },
        ))

    result.summary = {
        "probes_checked": len(checked),
        "current_matches": matches,
        "mismatches": mismatches,
        "confirmed_mismatches": confirmed_mismatches,
        "unavailable": unavailable,
        "alerts": len(result.alerts),
    }
    result.add_metric("deployment_probes_checked", len(checked))
    result.add_metric("deployment_probes_matching", result.summary["current_matches"])
    result.add_metric("deployment_mismatches", mismatches)
    return result
