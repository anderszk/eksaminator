import uuid
from typing import Optional

from fastapi import APIRouter

router = APIRouter(tags=["content"])


@router.get("/documents/{doc_id}/map")
async def get_map(doc_id: uuid.UUID):
    raise NotImplementedError


@router.get("/documents/{doc_id}/summaries")
async def get_summaries(doc_id: uuid.UUID, scope: Optional[str] = None):
    raise NotImplementedError


@router.get("/documents/{doc_id}/claims")
async def get_claims(doc_id: uuid.UUID):
    raise NotImplementedError


@router.get("/documents/{doc_id}/vulnerabilities")
async def get_vulnerabilities(doc_id: uuid.UUID):
    raise NotImplementedError


@router.get("/documents/{doc_id}/questions")
async def get_questions(
    doc_id: uuid.UUID,
    category: Optional[str] = None,
    difficulty: Optional[int] = None,
    limit: Optional[int] = None,
    unattempted: bool = False,
):
    raise NotImplementedError


@router.patch("/questions/{question_id}")
async def patch_question(question_id: uuid.UUID, body: dict):
    raise NotImplementedError


@router.get("/questions/{question_id}/audio")
async def get_question_audio(question_id: uuid.UUID):
    raise NotImplementedError


@router.get("/stats/coverage")
async def stats_coverage(document_id: Optional[uuid.UUID] = None):
    raise NotImplementedError


@router.get("/stats/weakest")
async def stats_weakest(document_id: Optional[uuid.UUID] = None, limit: int = 10):
    raise NotImplementedError


@router.get("/stats/progress")
async def stats_progress(document_id: Optional[uuid.UUID] = None):
    raise NotImplementedError


@router.get("/plan")
async def get_plan(document_id: Optional[uuid.UUID] = None):
    raise NotImplementedError


@router.patch("/plan/{item_id}")
async def patch_plan_item(item_id: uuid.UUID, body: dict):
    raise NotImplementedError
