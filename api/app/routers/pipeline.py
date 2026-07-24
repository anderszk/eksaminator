import uuid
from typing import Optional

from fastapi import APIRouter

from app.schemas.schemas import PipelineStatusOut

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


@router.post("/{doc_id}/run")
async def run_pipeline(
    doc_id: uuid.UUID,
    stages: Optional[str] = None,
    force: bool = False,
):
    raise NotImplementedError


@router.get("/{doc_id}/status", response_model=PipelineStatusOut)
async def pipeline_status(doc_id: uuid.UUID):
    raise NotImplementedError


@router.get("/runs/{run_id}")
async def get_run(run_id: uuid.UUID):
    raise NotImplementedError
