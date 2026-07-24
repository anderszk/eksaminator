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


@router.get("/stats/coverage")
async def stats_coverage(document_id: Optional[uuid.UUID] = None, db: AsyncSession = Depends(get_db)):
    if not document_id:
        return {"coverage": {}}

    # All questions by category
    q_result = await db.execute(
        select(Question.category, func.count(Question.id).label("total"))
        .where(Question.document_id == document_id, Question.retired == False)  # noqa: E712
        .group_by(Question.category)
    )
    totals = {row.category: row.total for row in q_result}

    # Mean scores per category (from graded turns)
    score_result = await db.execute(
        select(Question.category, Turn.scores)
        .join(Turn, Turn.question_id == Question.id)
        .where(Question.document_id == document_id, Turn.status == "graded")
    )
    rows = score_result.all()

    category_scores: dict[str, list[float]] = {}
    for row in rows:
        if row.scores:
            vals = list(row.scores.values())
            mean = sum(vals) / len(vals) if vals else 0
            category_scores.setdefault(row.category, []).append(mean)

    coverage = {}
    for cat, total in totals.items():
        scores = category_scores.get(cat, [])
        coverage[cat] = {
            "total": total,
            "attempted": len(scores),
            "mean_score": round(sum(scores) / len(scores), 2) if scores else None,
        }

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
        return {"sessions": []}

    from app.models.models import Session as SessionModel

    result = await db.execute(
        select(SessionModel)
        .where(SessionModel.document_id == document_id)
        .order_by(SessionModel.started_at)
    )
    sessions = result.scalars().all()

    progress = []
    for s in sessions:
        turns_result = await db.execute(
            select(Turn).where(Turn.session_id == s.id, Turn.status == "graded")
        )
        turns = turns_result.scalars().all()
        if not turns:
            continue
        all_scores = []
        total_wpm = []
        for t in turns:
            if t.scores:
                vals = list(t.scores.values())
                all_scores.append(sum(vals) / len(vals))
            if t.wpm:
                total_wpm.append(t.wpm)
        progress.append({
            "session_id": str(s.id),
            "mode": s.mode,
            "started_at": s.started_at.isoformat(),
            "questions": len(turns),
            "mean_score": round(sum(all_scores) / len(all_scores), 2) if all_scores else None,
            "mean_wpm": round(sum(total_wpm) / len(total_wpm), 1) if total_wpm else None,
        })

    return {"document_id": str(document_id), "sessions": progress}


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
