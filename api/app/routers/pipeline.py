import uuid
from typing import Optional

from arq import create_pool
from arq.connections import RedisSettings
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_db
from app.models.models import AnalysisRun, Document

router = APIRouter(prefix="/pipeline", tags=["pipeline"])

ALL_STAGES = ["ingest", "structure", "claims", "vulnerabilities", "questions", "answers", "summaries"]


async def _get_redis():
    return await create_pool(RedisSettings.from_dsn(settings.redis_url))


@router.post("/{doc_id}/run")
async def run_pipeline(
    doc_id: uuid.UUID,
    stages: Optional[str] = None,
    force: bool = False,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Dokument ikke funnet.")

    stage_list = [s.strip() for s in stages.split(",")] if stages else ALL_STAGES
    invalid = [s for s in stage_list if s not in ALL_STAGES]
    if invalid:
        raise HTTPException(400, f"Ukjente steg: {invalid}")

    redis = await _get_redis()
    job_ids = []
    try:
        for stage in stage_list:
            job = await redis.enqueue_job(
                "run_pipeline_stage",
                doc_id=str(doc_id),
                stage=stage,
                force=force,
            )
            job_ids.append(job.job_id if job else None)
    finally:
        await redis.aclose()

    return {"job_ids": job_ids, "stages": stage_list}


@router.get("/{doc_id}/status")
async def pipeline_status(doc_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Dokument ikke funnet.")

    # Get latest run per stage
    stages_out = {}
    total_cost = 0.0

    for stage in ALL_STAGES:
        runs_result = await db.execute(
            select(AnalysisRun)
            .where(AnalysisRun.document_id == doc_id, AnalysisRun.stage == stage)
            .order_by(AnalysisRun.created_at.desc())
            .limit(1)
        )
        run = runs_result.scalar_one_or_none()
        if run:
            stages_out[stage] = {
                "run_id": str(run.id),
                "status": run.status,
                "cost_usd": float(run.cost_usd or 0),
                "duration_ms": run.duration_ms,
                "error": run.error,
                "cached": run.status == "done",
                "created_at": run.created_at.isoformat() if run.created_at else None,
                "completed_at": run.completed_at.isoformat() if run.completed_at else None,
            }
            total_cost += float(run.cost_usd or 0)
        else:
            stages_out[stage] = {"status": "pending", "cost_usd": 0}

    return {
        "document_id": str(doc_id),
        "stages": stages_out,
        "total_cost_usd": round(total_cost, 4),
    }


@router.get("/runs/{run_id}")
async def get_run(run_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AnalysisRun).where(AnalysisRun.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(404, "Run ikke funnet.")
    return {
        "id": str(run.id),
        "document_id": str(run.document_id),
        "stage": run.stage,
        "status": run.status,
        "input_tokens": run.input_tokens,
        "output_tokens": run.output_tokens,
        "cost_usd": float(run.cost_usd or 0),
        "duration_ms": run.duration_ms,
        "error": run.error,
        "output": run.output,
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
    }
