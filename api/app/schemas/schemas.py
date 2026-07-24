import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class DocumentOut(BaseModel):
    id: uuid.UUID
    filename: str
    sha256: str
    page_count: int
    char_count: int
    language: str
    title: Optional[str]
    uploaded_at: datetime

    model_config = {"from_attributes": True}


class DocumentUploadOut(BaseModel):
    id: uuid.UUID
    sha256: str
    existing: bool


class DocumentRenameIn(BaseModel):
    title: str


class AnalysisRunOut(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    stage: str
    status: str
    input_tokens: int
    output_tokens: int
    cost_usd: Optional[float]
    duration_ms: Optional[int]
    error: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]

    model_config = {"from_attributes": True}


class PipelineStatusOut(BaseModel):
    document_id: uuid.UUID
    stages: dict[str, AnalysisRunOut]
    total_cost_usd: float


class QuestionOut(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    category: str
    difficulty: int
    text: str
    why_asked: str
    expected_shape: str
    source_refs: list[Any]
    follow_ups: list[Any]
    model_answer: Optional[str]
    rubric: Optional[dict]
    tts_key: Optional[str]
    retired: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class SessionCreate(BaseModel):
    document_id: uuid.UUID
    mode: str
    config: dict = {}


class SessionOut(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    mode: str
    config: dict
    started_at: datetime
    ended_at: Optional[datetime]

    model_config = {"from_attributes": True}


class TurnOut(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    question_id: uuid.UUID
    ordinal: int
    status: str
    transcript: Optional[str]
    scores: Optional[dict]
    feedback_md: Optional[str]
    wpm: Optional[float]
    duration_ms: Optional[int]
    filler_count: Optional[int]

    model_config = {"from_attributes": True}


class PlanItemOut(BaseModel):
    id: uuid.UUID
    document_id: Optional[uuid.UUID]
    day: int
    title: str
    detail_md: Optional[str]
    minutes: Optional[int]
    kind: str
    done: bool
    linked_categories: Optional[list[str]]
    ordinal: int

    model_config = {"from_attributes": True}
