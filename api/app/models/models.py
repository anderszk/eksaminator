import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import ARRAY, ENUM, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base

# Native Postgres enum types (created by the 001_initial migration) — create_type=False
# so SQLAlchemy binds/casts against the existing type instead of trying to create it.
PipelineStage = ENUM(
    "ingest", "structure", "claims", "vulnerabilities", "questions", "answers", "summaries",
    name="pipeline_stage", create_type=False,
)
RunStatus = ENUM("pending", "running", "done", "failed", "stale", name="run_status", create_type=False)
SessionMode = ENUM("drill", "exam", name="session_mode", create_type=False)
TurnStatus = ENUM(
    "pending", "recorded", "transcribed", "graded", "skipped", name="turn_status", create_type=False,
)


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename: Mapped[str] = mapped_column(sa.Text)
    sha256: Mapped[str] = mapped_column(sa.Text, unique=True)
    page_count: Mapped[int]
    char_count: Mapped[int]
    language: Mapped[str] = mapped_column(sa.Text, default="no")
    s3_key: Mapped[str] = mapped_column(sa.Text)
    title: Mapped[Optional[str]] = mapped_column(sa.Text)
    uploaded_at: Mapped[datetime] = mapped_column(sa.TIMESTAMP(timezone=True), server_default=sa.func.now())


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"))
    ordinal: Mapped[int]
    page_start: Mapped[int]
    page_end: Mapped[int]
    section_path: Mapped[Optional[str]] = mapped_column(sa.Text)
    kind: Mapped[str] = mapped_column(sa.Text, default="text")
    text: Mapped[str] = mapped_column(sa.Text)
    token_count: Mapped[int]
    embedding: Mapped[Optional[Any]] = mapped_column(Vector(1024))

    __table_args__ = (sa.UniqueConstraint("document_id", "ordinal"),)


class AnalysisRun(Base):
    __tablename__ = "analysis_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"))
    stage: Mapped[str] = mapped_column(PipelineStage)
    cache_key: Mapped[str] = mapped_column(sa.Text)
    prompt_version: Mapped[str] = mapped_column(sa.Text)
    model: Mapped[str] = mapped_column(sa.Text)
    params_hash: Mapped[str] = mapped_column(sa.Text)
    status: Mapped[str] = mapped_column(RunStatus, default="pending")
    input_tokens: Mapped[int] = mapped_column(default=0)
    output_tokens: Mapped[int] = mapped_column(default=0)
    cost_usd: Mapped[Optional[Decimal]] = mapped_column(sa.Numeric(10, 4), default=0)
    duration_ms: Mapped[Optional[int]]
    error: Mapped[Optional[str]] = mapped_column(sa.Text)
    output: Mapped[Optional[dict]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(sa.TIMESTAMP(timezone=True), server_default=sa.func.now())
    completed_at: Mapped[Optional[datetime]] = mapped_column(sa.TIMESTAMP(timezone=True))


class ThesisMap(Base):
    __tablename__ = "thesis_map"

    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), sa.ForeignKey("analysis_runs.id", ondelete="CASCADE"), primary_key=True)
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"))
    data: Mapped[dict] = mapped_column(JSONB)


class Claim(Base):
    __tablename__ = "claims"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), sa.ForeignKey("analysis_runs.id", ondelete="CASCADE"))
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"))
    text: Mapped[str] = mapped_column(sa.Text)
    claim_type: Mapped[str] = mapped_column(sa.Text)
    evidence_refs: Mapped[list] = mapped_column(JSONB)
    strength: Mapped[int] = mapped_column(sa.Integer, sa.CheckConstraint("strength BETWEEN 1 AND 5"))
    created_at: Mapped[datetime] = mapped_column(sa.TIMESTAMP(timezone=True), server_default=sa.func.now())


class Vulnerability(Base):
    __tablename__ = "vulnerabilities"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), sa.ForeignKey("analysis_runs.id", ondelete="CASCADE"))
    claim_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), sa.ForeignKey("claims.id", ondelete="CASCADE"))
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"))
    checklist_key: Mapped[str] = mapped_column(sa.Text)
    description: Mapped[str] = mapped_column(sa.Text)
    severity: Mapped[int] = mapped_column(sa.Integer, sa.CheckConstraint("severity BETWEEN 1 AND 5"))
    attack_angle: Mapped[str] = mapped_column(sa.Text)
    best_defence: Mapped[Optional[str]] = mapped_column(sa.Text)


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), sa.ForeignKey("analysis_runs.id", ondelete="CASCADE"))
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"))
    claim_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), sa.ForeignKey("claims.id", ondelete="SET NULL"))
    vulnerability_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), sa.ForeignKey("vulnerabilities.id", ondelete="SET NULL"))
    category: Mapped[str] = mapped_column(sa.Text)
    difficulty: Mapped[int] = mapped_column(sa.Integer, sa.CheckConstraint("difficulty BETWEEN 1 AND 4"))
    text: Mapped[str] = mapped_column(sa.Text)
    why_asked: Mapped[str] = mapped_column(sa.Text)
    expected_shape: Mapped[str] = mapped_column(sa.Text)
    source_refs: Mapped[list] = mapped_column(JSONB)
    follow_ups: Mapped[list] = mapped_column(JSONB, default=list)
    model_answer: Mapped[Optional[str]] = mapped_column(sa.Text)
    rubric: Mapped[Optional[dict]] = mapped_column(JSONB)
    tts_key: Mapped[Optional[str]] = mapped_column(sa.Text)
    retired: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(sa.TIMESTAMP(timezone=True), server_default=sa.func.now())


class Summary(Base):
    __tablename__ = "summaries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), sa.ForeignKey("analysis_runs.id", ondelete="CASCADE"))
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"))
    scope: Mapped[str] = mapped_column(sa.Text)
    ref: Mapped[str] = mapped_column(sa.Text)
    title: Mapped[str] = mapped_column(sa.Text)
    body_md: Mapped[str] = mapped_column(sa.Text)
    source_refs: Mapped[list] = mapped_column(JSONB)
    ordinal: Mapped[int] = mapped_column(default=0)


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"))
    mode: Mapped[str] = mapped_column(SessionMode)
    config: Mapped[dict] = mapped_column(JSONB, default=dict)
    started_at: Mapped[datetime] = mapped_column(sa.TIMESTAMP(timezone=True), server_default=sa.func.now())
    ended_at: Mapped[Optional[datetime]] = mapped_column(sa.TIMESTAMP(timezone=True))
    summary: Mapped[Optional[dict]] = mapped_column(JSONB)


class Turn(Base):
    __tablename__ = "turns"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), sa.ForeignKey("sessions.id", ondelete="CASCADE"))
    question_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), sa.ForeignKey("questions.id", ondelete="CASCADE"))
    ordinal: Mapped[int]
    status: Mapped[str] = mapped_column(TurnStatus, default="pending")
    is_follow_up: Mapped[bool] = mapped_column(default=False)
    parent_turn_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), sa.ForeignKey("turns.id", ondelete="SET NULL"))

    answer_s3_key: Mapped[Optional[str]] = mapped_column(sa.Text)
    transcript: Mapped[Optional[str]] = mapped_column(sa.Text)
    stt_confidence: Mapped[Optional[float]] = mapped_column(sa.Float)

    duration_ms: Mapped[Optional[int]]
    wpm: Mapped[Optional[float]] = mapped_column(sa.Float)
    filler_count: Mapped[Optional[int]]
    filler_rate: Mapped[Optional[float]] = mapped_column(sa.Float)
    longest_pause_ms: Mapped[Optional[int]]
    time_to_first_word_ms: Mapped[Optional[int]]

    scores: Mapped[Optional[dict]] = mapped_column(JSONB)
    bluffed: Mapped[Optional[bool]]
    used_shape: Mapped[Optional[str]] = mapped_column(sa.Text)
    feedback_md: Mapped[Optional[str]] = mapped_column(sa.Text)
    missed_points: Mapped[Optional[list]] = mapped_column(JSONB)

    asked_at: Mapped[Optional[datetime]] = mapped_column(sa.TIMESTAMP(timezone=True))
    answered_at: Mapped[Optional[datetime]] = mapped_column(sa.TIMESTAMP(timezone=True))
    graded_at: Mapped[Optional[datetime]] = mapped_column(sa.TIMESTAMP(timezone=True))

    __table_args__ = (sa.UniqueConstraint("session_id", "ordinal"),)


class PlanItem(Base):
    __tablename__ = "plan_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"))
    day: Mapped[int] = mapped_column(sa.Integer, sa.CheckConstraint("day BETWEEN 1 AND 14"))
    title: Mapped[str] = mapped_column(sa.Text)
    detail_md: Mapped[Optional[str]] = mapped_column(sa.Text)
    minutes: Mapped[Optional[int]]
    kind: Mapped[str] = mapped_column(sa.Text)
    done: Mapped[bool] = mapped_column(default=False)
    linked_categories: Mapped[Optional[list]] = mapped_column(ARRAY(sa.Text), default=list)
    ordinal: Mapped[int] = mapped_column(default=0)
