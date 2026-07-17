from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from .models import (
    AiVisibilityObservation,
    Alert,
    Base,
    JobRun,
    KeywordCandidate,
    KeywordRanking,
    LocalRanking,
    Metric,
    PageSnapshot,
)
from .types import AlertSpec, CheckResult


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def normalize_database_url(database_url: str) -> str:
    """Use the installed psycopg v3 driver for Railway PostgreSQL URLs."""
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    if database_url.startswith("postgres://"):
        return database_url.replace("postgres://", "postgresql+psycopg://", 1)
    return database_url


class Store:
    def __init__(self, database_url: str):
        if database_url.startswith("sqlite:///"):
            db_path = Path(database_url.removeprefix("sqlite:///"))
            db_path.parent.mkdir(parents=True, exist_ok=True)
        self.engine = create_engine(normalize_database_url(database_url), pool_pre_ping=True)
        self.sessions = sessionmaker(self.engine, expire_on_commit=False)

    def initialize(self) -> None:
        Base.metadata.create_all(self.engine)

    def start_job(self, job_name: str) -> int:
        with self.sessions.begin() as session:
            run = JobRun(job_name=job_name, status="running")
            session.add(run)
            session.flush()
            return run.id

    def fail_job(self, run_id: int, error: str) -> None:
        with self.sessions.begin() as session:
            run = session.get(JobRun, run_id)
            if run:
                run.status = "failed"
                run.finished_at = utcnow()
                run.error = error

    def fail_stale_runs(self, stale_before: datetime) -> int:
        now = utcnow()
        with self.sessions.begin() as session:
            runs = session.scalars(
                select(JobRun).where(
                    JobRun.status == "running",
                    JobRun.started_at < stale_before,
                )
            ).all()
            for run in runs:
                run.status = "failed"
                run.finished_at = now
                run.error = "Ejecución interrumpida: superó el tiempo máximo sin finalizar."
            return len(runs)

    def save_result(self, run_id: int, result: CheckResult) -> list[Alert]:
        now = utcnow()
        seen_keys = {item.dedupe_key for item in result.alerts}
        changed_alerts: list[Alert] = []
        with self.sessions.begin() as session:
            run = session.get(JobRun, run_id)
            if not run:
                raise RuntimeError(f"Unknown job run {run_id}")
            run.status = result.status
            run.finished_at = now
            run.summary_json = json.dumps(result.summary, ensure_ascii=False, sort_keys=True)

            for metric in result.metrics:
                session.add(Metric(
                    source=metric["source"],
                    name=metric["name"],
                    value=metric["value"],
                    dimensions_json=json.dumps(metric["dimensions"], ensure_ascii=False, sort_keys=True),
                    job_run_id=run_id,
                ))

            for spec in result.alerts:
                alert = session.scalar(select(Alert).where(Alert.dedupe_key == spec.dedupe_key))
                if alert is None:
                    alert = Alert(
                        dedupe_key=spec.dedupe_key,
                        severity=spec.severity,
                        category=spec.category,
                        title=spec.title,
                        message=spec.message,
                        action=spec.action,
                        evidence_url=spec.evidence_url,
                        metadata_json=json.dumps(spec.metadata, ensure_ascii=False, sort_keys=True),
                        status="open",
                        first_seen_at=now,
                        last_seen_at=now,
                        last_job_run_id=run_id,
                    )
                    session.add(alert)
                    changed_alerts.append(alert)
                else:
                    was_open = alert.status == "open"
                    alert.severity = spec.severity
                    alert.category = spec.category
                    alert.title = spec.title
                    alert.message = spec.message
                    alert.action = spec.action
                    alert.evidence_url = spec.evidence_url
                    alert.metadata_json = json.dumps(spec.metadata, ensure_ascii=False, sort_keys=True)
                    alert.status = "open"
                    alert.resolved_at = None
                    alert.last_seen_at = now
                    alert.last_job_run_id = run_id
                    alert.occurrences += 1
                    if not was_open:
                        changed_alerts.append(alert)

            if result.status == "success":
                open_for_job = session.scalars(
                    select(Alert).where(
                        Alert.status == "open",
                        Alert.category == result.job_name,
                    )
                ).all()
                for alert in open_for_job:
                    if alert.dedupe_key not in seen_keys:
                        alert.status = "resolved"
                        alert.resolved_at = now
                        alert.last_job_run_id = run_id
                        changed_alerts.append(alert)
        return changed_alerts

    def add_page_snapshot(self, run_id: int, source: str, payload: dict) -> None:
        with self.sessions.begin() as session:
            session.add(PageSnapshot(
                source=source,
                url=payload["url"],
                status_code=payload.get("status_code"),
                final_url=payload.get("final_url"),
                elapsed_ms=payload.get("elapsed_ms"),
                title=payload.get("title"),
                canonical=payload.get("canonical"),
                robots=payload.get("robots"),
                content_hash=payload.get("content_hash"),
                payload_json=json.dumps(payload, ensure_ascii=False, sort_keys=True),
                job_run_id=run_id,
            ))

    def latest_page_snapshot(self, source: str, url: str) -> PageSnapshot | None:
        with self.sessions() as session:
            return session.scalar(
                select(PageSnapshot)
                .where(PageSnapshot.source == source, PageSnapshot.url == url)
                .order_by(PageSnapshot.observed_at.desc())
            )

    def add_keyword_ranking(self, run_id: int, payload: dict) -> None:
        with self.sessions.begin() as session:
            session.add(KeywordRanking(
                keyword=payload["keyword"],
                language_code=payload["language_code"],
                location_name=payload["location_name"],
                device=payload["device"],
                cluster=payload["cluster"],
                target_url=payload["target_url"],
                position=payload.get("position"),
                ranking_url=payload.get("ranking_url"),
                top_domain=payload.get("top_domain"),
                payload_json=json.dumps(payload, ensure_ascii=False, sort_keys=True),
                job_run_id=run_id,
            ))

    def keyword_candidate_count(self, status: str = "active") -> int:
        with self.sessions() as session:
            return int(session.scalar(
                select(func.count(KeywordCandidate.id)).where(KeywordCandidate.status == status)
            ) or 0)

    def upsert_keyword_candidate(self, run_id: int, payload: dict) -> tuple[KeywordCandidate, bool, bool]:
        now = utcnow()
        normalized_query = " ".join(str(payload["query"]).casefold().split())
        with self.sessions.begin() as session:
            candidate = session.scalar(
                select(KeywordCandidate).where(KeywordCandidate.query == normalized_query)
            )
            created = candidate is None
            previous_status = candidate.status if candidate else None
            if candidate is None:
                candidate = KeywordCandidate(query=normalized_query, first_seen_at=now)
                session.add(candidate)
            candidate.language_code = payload["language_code"]
            candidate.location_name = payload["location_name"]
            candidate.location_code = str(payload.get("location_code") or "")
            candidate.device = payload.get("device", "mobile")
            candidate.cluster = payload["cluster"]
            candidate.target_url = payload["target_url"]
            candidate.priority = payload.get("priority", "P1")
            if candidate.status != "active":
                candidate.status = payload.get("status", "candidate")
            candidate.source = payload.get("source", "gsc")
            candidate.impressions = float(payload.get("impressions", 0) or 0)
            candidate.clicks = float(payload.get("clicks", 0) or 0)
            candidate.ctr = float(payload.get("ctr", 0) or 0)
            candidate.position = float(payload.get("position", 0) or 0)
            candidate.last_seen_at = now
            candidate.last_job_run_id = run_id
            session.flush()
            activated = previous_status != "active" and candidate.status == "active"
            return candidate, created, activated

    def active_keyword_candidates(self, limit: int = 20) -> list[KeywordCandidate]:
        with self.sessions() as session:
            return list(session.scalars(
                select(KeywordCandidate)
                .where(KeywordCandidate.status == "active")
                .order_by(KeywordCandidate.impressions.desc(), KeywordCandidate.last_seen_at.desc())
                .limit(limit)
            ).all())

    def previous_keyword_ranking(self, keyword: str, location_name: str, device: str) -> KeywordRanking | None:
        history = self.keyword_ranking_history(keyword, location_name, device, limit=1)
        return history[0] if history else None

    def keyword_ranking_history(
        self,
        keyword: str,
        location_name: str,
        device: str,
        limit: int = 7,
    ) -> list[KeywordRanking]:
        with self.sessions() as session:
            return list(session.scalars(
                select(KeywordRanking)
                .where(
                    KeywordRanking.keyword == keyword,
                    KeywordRanking.location_name == location_name,
                    KeywordRanking.device == device,
                )
                .order_by(KeywordRanking.observed_at.desc())
                .limit(limit)
            ).all())

    def add_local_ranking(self, run_id: int, payload: dict) -> None:
        with self.sessions.begin() as session:
            session.add(LocalRanking(
                keyword=payload["keyword"],
                language_code=payload["language_code"],
                location_label=payload["location_label"],
                location_coordinate=payload["location_coordinate"],
                position=payload.get("position"),
                title=payload.get("title"),
                cid=payload.get("cid"),
                place_id=payload.get("place_id"),
                rating=payload.get("rating"),
                reviews_count=payload.get("reviews_count"),
                payload_json=json.dumps(payload, ensure_ascii=False, sort_keys=True),
                job_run_id=run_id,
            ))

    def previous_local_ranking(self, keyword: str, location_label: str) -> LocalRanking | None:
        history = self.local_ranking_history(keyword, location_label, limit=1)
        return history[0] if history else None

    def local_ranking_history(
        self,
        keyword: str,
        location_label: str,
        limit: int = 7,
    ) -> list[LocalRanking]:
        with self.sessions() as session:
            return list(session.scalars(
                select(LocalRanking)
                .where(LocalRanking.keyword == keyword, LocalRanking.location_label == location_label)
                .order_by(LocalRanking.observed_at.desc())
                .limit(limit)
            ).all())

    def add_ai_visibility_observation(self, run_id: int, payload: dict) -> None:
        with self.sessions.begin() as session:
            session.add(AiVisibilityObservation(
                prompt_id=payload["prompt_id"],
                prompt=payload["prompt"],
                language_code=payload["language_code"],
                market=payload["market"],
                provider=payload["provider"],
                model_name=payload.get("model_name"),
                voyager_mentioned=int(bool(payload.get("voyager_mentioned"))),
                voyager_cited=int(bool(payload.get("voyager_cited"))),
                competitor_mentions_json=json.dumps(payload.get("competitor_mentions", []), ensure_ascii=False, sort_keys=True),
                citations_json=json.dumps(payload.get("citations", []), ensure_ascii=False, sort_keys=True),
                response_text=payload.get("response_text", ""),
                payload_json=json.dumps(payload, ensure_ascii=False, sort_keys=True),
                job_run_id=run_id,
            ))

    def previous_ai_visibility(self, prompt_id: str, provider: str) -> AiVisibilityObservation | None:
        with self.sessions() as session:
            return session.scalar(
                select(AiVisibilityObservation)
                .where(
                    AiVisibilityObservation.prompt_id == prompt_id,
                    AiVisibilityObservation.provider == provider,
                )
                .order_by(AiVisibilityObservation.observed_at.desc())
            )

    def latest_success(self, job_name: str) -> JobRun | None:
        with self.sessions() as session:
            return session.scalar(
                select(JobRun)
                .where(JobRun.job_name == job_name, JobRun.status == "success")
                .order_by(JobRun.finished_at.desc())
            )

    def latest_run(self, job_name: str) -> JobRun | None:
        with self.sessions() as session:
            return session.scalar(
                select(JobRun)
                .where(JobRun.job_name == job_name)
                .order_by(JobRun.started_at.desc())
            )

    def open_alerts(self) -> list[Alert]:
        with self.sessions() as session:
            return list(session.scalars(
                select(Alert).where(Alert.status == "open").order_by(Alert.severity, Alert.last_seen_at.desc())
            ).all())

    def recent_runs(self, limit: int = 30) -> Iterable[JobRun]:
        with self.sessions() as session:
            return list(session.scalars(select(JobRun).order_by(JobRun.started_at.desc()).limit(limit)).all())

    def metric_sum_since(self, name: str, since: datetime, sources: set[str] | None = None) -> float:
        with self.sessions() as session:
            query = select(func.coalesce(func.sum(Metric.value), 0.0)).where(
                Metric.name == name,
                Metric.observed_at >= since,
            )
            if sources:
                query = query.where(Metric.source.in_(sources))
            return float(session.scalar(query) or 0.0)
