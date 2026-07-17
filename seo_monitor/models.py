from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Float, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class JobRun(Base):
    __tablename__ = "job_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_name: Mapped[str] = mapped_column(String(80), index=True)
    started_at: Mapped[datetime] = mapped_column(default=utcnow, index=True)
    finished_at: Mapped[Optional[datetime]]
    status: Mapped[str] = mapped_column(String(24), default="running", index=True)
    summary_json: Mapped[str] = mapped_column(Text, default="{}")
    error: Mapped[Optional[str]] = mapped_column(Text)


class Metric(Base):
    __tablename__ = "metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    observed_at: Mapped[datetime] = mapped_column(default=utcnow, index=True)
    source: Mapped[str] = mapped_column(String(80), index=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    value: Mapped[float] = mapped_column(Float)
    dimensions_json: Mapped[str] = mapped_column(Text, default="{}")
    job_run_id: Mapped[Optional[int]] = mapped_column(Integer, index=True)


class Alert(Base):
    __tablename__ = "alerts"
    __table_args__ = (UniqueConstraint("dedupe_key", name="uq_alert_dedupe_key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dedupe_key: Mapped[str] = mapped_column(String(300), index=True)
    severity: Mapped[str] = mapped_column(String(4), index=True)
    category: Mapped[str] = mapped_column(String(80), index=True)
    title: Mapped[str] = mapped_column(String(240))
    message: Mapped[str] = mapped_column(Text)
    action: Mapped[str] = mapped_column(Text)
    evidence_url: Mapped[Optional[str]] = mapped_column(Text)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    status: Mapped[str] = mapped_column(String(24), default="open", index=True)
    first_seen_at: Mapped[datetime] = mapped_column(default=utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(default=utcnow, index=True)
    resolved_at: Mapped[Optional[datetime]]
    occurrences: Mapped[int] = mapped_column(Integer, default=1)
    last_job_run_id: Mapped[Optional[int]] = mapped_column(Integer, index=True)


class PageSnapshot(Base):
    __tablename__ = "page_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    observed_at: Mapped[datetime] = mapped_column(default=utcnow, index=True)
    source: Mapped[str] = mapped_column(String(80), index=True)
    url: Mapped[str] = mapped_column(Text)
    status_code: Mapped[Optional[int]]
    final_url: Mapped[Optional[str]] = mapped_column(Text)
    elapsed_ms: Mapped[Optional[float]]
    title: Mapped[Optional[str]] = mapped_column(Text)
    canonical: Mapped[Optional[str]] = mapped_column(Text)
    robots: Mapped[Optional[str]] = mapped_column(Text)
    content_hash: Mapped[Optional[str]] = mapped_column(String(64), index=True)
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    job_run_id: Mapped[Optional[int]] = mapped_column(Integer, index=True)


class KeywordRanking(Base):
    __tablename__ = "keyword_rankings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    observed_at: Mapped[datetime] = mapped_column(default=utcnow, index=True)
    keyword: Mapped[str] = mapped_column(Text)
    language_code: Mapped[str] = mapped_column(String(10))
    location_name: Mapped[str] = mapped_column(Text)
    device: Mapped[str] = mapped_column(String(20))
    cluster: Mapped[str] = mapped_column(String(80), index=True)
    target_url: Mapped[str] = mapped_column(Text)
    position: Mapped[Optional[float]]
    ranking_url: Mapped[Optional[str]] = mapped_column(Text)
    top_domain: Mapped[Optional[str]] = mapped_column(Text)
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    job_run_id: Mapped[Optional[int]] = mapped_column(Integer, index=True)


class KeywordCandidate(Base):
    __tablename__ = "keyword_candidates"
    __table_args__ = (UniqueConstraint("query", name="uq_keyword_candidate_query"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    query: Mapped[str] = mapped_column(Text, index=True)
    language_code: Mapped[str] = mapped_column(String(10))
    location_name: Mapped[str] = mapped_column(Text)
    location_code: Mapped[str] = mapped_column(String(20))
    device: Mapped[str] = mapped_column(String(20), default="mobile")
    cluster: Mapped[str] = mapped_column(String(80), index=True)
    target_url: Mapped[str] = mapped_column(Text)
    priority: Mapped[str] = mapped_column(String(4), default="P1")
    status: Mapped[str] = mapped_column(String(24), default="candidate", index=True)
    source: Mapped[str] = mapped_column(String(40), default="gsc")
    impressions: Mapped[float] = mapped_column(Float, default=0)
    clicks: Mapped[float] = mapped_column(Float, default=0)
    ctr: Mapped[float] = mapped_column(Float, default=0)
    position: Mapped[float] = mapped_column(Float, default=0)
    first_seen_at: Mapped[datetime] = mapped_column(default=utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(default=utcnow, index=True)
    last_job_run_id: Mapped[Optional[int]] = mapped_column(Integer, index=True)


class LocalRanking(Base):
    __tablename__ = "local_rankings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    observed_at: Mapped[datetime] = mapped_column(default=utcnow, index=True)
    keyword: Mapped[str] = mapped_column(Text)
    language_code: Mapped[str] = mapped_column(String(10))
    location_label: Mapped[str] = mapped_column(String(120), index=True)
    location_coordinate: Mapped[str] = mapped_column(String(80))
    position: Mapped[Optional[float]]
    title: Mapped[Optional[str]] = mapped_column(Text)
    cid: Mapped[Optional[str]] = mapped_column(String(80), index=True)
    place_id: Mapped[Optional[str]] = mapped_column(String(300), index=True)
    rating: Mapped[Optional[float]]
    reviews_count: Mapped[Optional[int]]
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    job_run_id: Mapped[Optional[int]] = mapped_column(Integer, index=True)


class AiVisibilityObservation(Base):
    __tablename__ = "ai_visibility_observations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    observed_at: Mapped[datetime] = mapped_column(default=utcnow, index=True)
    prompt_id: Mapped[str] = mapped_column(String(120), index=True)
    prompt: Mapped[str] = mapped_column(Text)
    language_code: Mapped[str] = mapped_column(String(10))
    market: Mapped[str] = mapped_column(String(80), index=True)
    provider: Mapped[str] = mapped_column(String(40), index=True)
    model_name: Mapped[Optional[str]] = mapped_column(String(160))
    voyager_mentioned: Mapped[int] = mapped_column(Integer, default=0)
    voyager_cited: Mapped[int] = mapped_column(Integer, default=0)
    competitor_mentions_json: Mapped[str] = mapped_column(Text, default="[]")
    citations_json: Mapped[str] = mapped_column(Text, default="[]")
    response_text: Mapped[str] = mapped_column(Text, default="")
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    job_run_id: Mapped[Optional[int]] = mapped_column(Integer, index=True)
