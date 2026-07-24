import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.models import (
    Claim,
    PlanItem,
    Question,
    Summary,
    ThesisMap,
    Turn,
    Vulnerability,
)

router = APIRouter(tags=["content"])


@router.get("/documents/{doc_id}/map")
async def get_map(doc_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ThesisMap).where(ThesisMap.document_id == doc_id))
    tm = result.scalar_one_or_none()
    if not tm:
        raise HTTPException(404, "Strukturkart ikke klart ennå.")
    return tm.data


@router.get("/documents/{doc_id}/summaries")
async def get_summaries(doc_id: uuid.UUID, scope: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    q = select(Summary).where(Summary.document_id == doc_id)
    if scope:
        q = q.where(Summary.scope == scope)
    q = q.order_by(Summary.scope, Summary.ordinal)
    result = await db.execute(q)
    summaries = result.scalars().all()
    return [
        {
            "id": str(s.id),
            "scope": s.scope,
            "ref": s.ref,
            "title": s.title,
            "body_md": s.body_md,
            "source_refs": s.source_refs,
            "ordinal": s.ordinal,
        }
        for s in summaries
    ]


@router.get("/documents/{doc_id}/claims")
async def get_claims(doc_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Claim).where(Claim.document_id == doc_id).order_by(Claim.strength.desc())
    )
    claims = result.scalars().all()
    return [
        {
            "id": str(c.id),
            "text": c.text,
            "claim_type": c.claim_type,
            "evidence_refs": c.evidence_refs,
            "strength": c.strength,
        }
        for c in claims
    ]


@router.get("/documents/{doc_id}/vulnerabilities")
async def get_vulnerabilities(doc_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Vulnerability).where(Vulnerability.document_id == doc_id).order_by(Vulnerability.severity.desc())
    )
    vulns = result.scalars().all()
    return [
        {
            "id": str(v.id),
            "checklist_key": v.checklist_key,
            "description": v.description,
            "severity": v.severity,
            "attack_angle": v.attack_angle,
            "best_defence": v.best_defence,
        }
        for v in vulns
    ]


@router.get("/documents/{doc_id}/questions")
async def get_questions(
    doc_id: uuid.UUID,
    category: Optional[str] = None,
    difficulty: Optional[int] = None,
    limit: Optional[int] = None,
    unattempted: bool = False,
    db: AsyncSession = Depends(get_db),
):
    q = select(Question).where(Question.document_id == doc_id, Question.retired == False)  # noqa: E712
    if category:
        q = q.where(Question.category == category)
    if difficulty:
        q = q.where(Question.difficulty == difficulty)
    if unattempted:
        # Questions that appear in no turns
        attempted_ids = select(Turn.question_id).distinct()
        q = q.where(Question.id.not_in(attempted_ids))
    if limit:
        q = q.limit(limit)
    q = q.order_by(Question.category, Question.difficulty)
    result = await db.execute(q)
    questions = result.scalars().all()
    return [
        {
            "id": str(qu.id),
            "document_id": str(qu.document_id),
            "category": qu.category,
            "difficulty": qu.difficulty,
            "text": qu.text,
            "why_asked": qu.why_asked,
            "expected_shape": qu.expected_shape,
            "source_refs": qu.source_refs,
            "follow_ups": qu.follow_ups,
            "model_answer": qu.model_answer,
            "rubric": qu.rubric,
            "tts_key": qu.tts_key,
            "retired": qu.retired,
            "created_at": qu.created_at.isoformat(),
        }
        for qu in questions
    ]


@router.patch("/questions/{question_id}")
async def patch_question(question_id: uuid.UUID, body: dict, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Question).where(Question.id == question_id))
    q = result.scalar_one_or_none()
    if not q:
        raise HTTPException(404, "Spørsmål ikke funnet.")
    if "retired" in body:
        q.retired = bool(body["retired"])
    if "text" in body:
        q.text = str(body["text"])
    await db.commit()
    return {"id": str(q.id), "retired": q.retired}


@router.get("/questions/{question_id}/audio")
async def get_question_audio(question_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    import asyncio
    from app.config import settings
    from app.services import tts as tts_service

    result = await db.execute(select(Question).where(Question.id == question_id))
    q = result.scalar_one_or_none()
    if not q:
        raise HTTPException(404, "Spørsmål ikke funnet.")

    voice = settings.piper_voice
    if not q.tts_key:
        s3_key = await tts_service.synthesize_and_cache(
            str(q.id), q.text, voice, settings.prompt_version
        )
        q.tts_key = s3_key
        await db.commit()

    url = await asyncio.to_thread(lambda: tts_service.get_presigned_url(q.tts_key))
    return {"url": url}


def _chapter_of(source_refs: Optional[list]) -> str:
    if not source_refs:
        return "Ukjent"
    path = source_refs[0].get("section_path") if isinstance(source_refs[0], dict) else None
    if not path:
        return "Ukjent"
    return path.split(">")[0].strip()


@router.get("/stats/coverage")
async def stats_coverage(document_id: Optional[uuid.UUID] = None, db: AsyncSession = Depends(get_db)):
    if not document_id:
        return {"coverage": []}

    # All questions — chapter × category grid, including unattempted cells
    q_result = await db.execute(
        select(Question.id, Question.category, Question.source_refs)
        .where(Question.document_id == document_id, Question.retired == False)  # noqa: E712
    )
    cells: dict[tuple[str, str], dict] = {}
    for row in q_result:
        key = (_chapter_of(row.source_refs), row.category)
        cells.setdefault(key, {"total": 0, "scores": []})["total"] += 1

    # Mean scores per (chapter, category), from graded turns
    score_result = await db.execute(
        select(Question.category, Question.source_refs, Turn.scores)
        .join(Turn, Turn.question_id == Question.id)
        .where(Question.document_id == document_id, Turn.status == "graded")
    )
    for row in score_result:
        if not row.scores:
            continue
        key = (_chapter_of(row.source_refs), row.category)
        vals = list(row.scores.values())
        mean = sum(vals) / len(vals) if vals else 0
        cells.setdefault(key, {"total": 0, "scores": []})["scores"].append(mean)

    coverage = [
        {
            "chapter": chapter,
            "category": category,
            "attempts": len(cell["scores"]),
            "mean_score": round(sum(cell["scores"]) / len(cell["scores"]), 2) if cell["scores"] else None,
        }
        for (chapter, category), cell in cells.items()
    ]

    return {"document_id": str(document_id), "coverage": coverage}


@router.get("/stats/weakest")
async def stats_weakest(
    document_id: Optional[uuid.UUID] = None,
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
):
    if not document_id:
        return {"questions": []}

    # Get all graded turns with scores
    result = await db.execute(
        select(Question, Turn)
        .join(Turn, Turn.question_id == Question.id)
        .where(Question.document_id == document_id, Turn.status == "graded")
    )
    rows = result.all()

    # Aggregate mean score per question
    question_scores: dict[str, dict] = {}
    for q, t in rows:
        qid = str(q.id)
        if qid not in question_scores:
            question_scores[qid] = {"question": q, "scores": []}
        if t.scores:
            vals = list(t.scores.values())
            question_scores[qid]["scores"].append(sum(vals) / len(vals))

    weakest = sorted(
        question_scores.values(),
        key=lambda x: sum(x["scores"]) / len(x["scores"]) if x["scores"] else 99,
    )[:limit]

    return {
        "questions": [
            {
                "id": str(item["question"].id),
                "text": item["question"].text,
                "category": item["question"].category,
                "difficulty": item["question"].difficulty,
                "mean_score": round(sum(item["scores"]) / len(item["scores"]), 2) if item["scores"] else None,
                "attempts": len(item["scores"]),
            }
            for item in weakest
        ]
    }


@router.get("/stats/progress")
async def stats_progress(document_id: Optional[uuid.UUID] = None, db: AsyncSession = Depends(get_db)):
    if not document_id:
        return {"progress": []}

    from app.models.models import Session as SessionModel

    result = await db.execute(
        select(SessionModel.id, SessionModel.started_at)
        .where(SessionModel.document_id == document_id)
        .order_by(SessionModel.started_at)
    )
    sessions = result.all()

    days: dict[str, dict] = {}
    for s in sessions:
        turns_result = await db.execute(
            select(Turn.scores).where(Turn.session_id == s.id, Turn.status == "graded")
        )
        scores = [row.scores for row in turns_result if row.scores]
        if not scores:
            continue
        date_key = s.started_at.date().isoformat()
        day = days.setdefault(date_key, {"scores": [], "sessions": set()})
        day["sessions"].add(s.id)
        for sc in scores:
            vals = list(sc.values())
            day["scores"].append(sum(vals) / len(vals))

    progress = [
        {
            "date": date_key,
            "mean_score": round(sum(day["scores"]) / len(day["scores"]), 2),
            "session_count": len(day["sessions"]),
        }
        for date_key, day in sorted(days.items())
    ]

    return {"document_id": str(document_id), "progress": progress}


@router.get("/plan")
async def get_plan(document_id: Optional[uuid.UUID] = None, db: AsyncSession = Depends(get_db)):
    q = select(PlanItem)
    if document_id:
        q = q.where(PlanItem.document_id == document_id)
    q = q.order_by(PlanItem.day, PlanItem.ordinal)
    result = await db.execute(q)
    items = result.scalars().all()
    return [
        {
            "id": str(item.id),
            "document_id": str(item.document_id) if item.document_id else None,
            "day": item.day,
            "title": item.title,
            "detail_md": item.detail_md,
            "minutes": item.minutes,
            "kind": item.kind,
            "done": item.done,
            "linked_categories": item.linked_categories or [],
            "ordinal": item.ordinal,
        }
        for item in items
    ]


@router.patch("/plan/{item_id}")
async def patch_plan_item(item_id: uuid.UUID, body: dict, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(PlanItem).where(PlanItem.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(404, "Planpunkt ikke funnet.")
    if "done" in body:
        item.done = bool(body["done"])
    await db.commit()
    return {"id": str(item.id), "done": item.done}
