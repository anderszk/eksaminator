import asyncio
import random
import uuid
from datetime import datetime, timezone

from arq import create_pool
from arq.connections import RedisSettings
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_db
from app.models.models import Question, Session, Turn
from app.schemas.schemas import SessionCreate, SessionOut
from app.services import tts as tts_service

router = APIRouter(prefix="/sessions", tags=["sessions"])


async def _weighted_draw(
    db: AsyncSession,
    document_id: uuid.UUID,
    session_id: uuid.UUID,
    config: dict,
) -> Question | None:
    """Select a question using weakest-first weighted draw."""
    # Build base query
    q = select(Question).where(
        Question.document_id == document_id,
        Question.retired == False,  # noqa: E712
    )

    if "categories" in config and config["categories"]:
        q = q.where(Question.category.in_(config["categories"]))
    if "difficulty_min" in config:
        q = q.where(Question.difficulty >= config["difficulty_min"])
    if "difficulty_max" in config:
        q = q.where(Question.difficulty <= config["difficulty_max"])

    # Exclude already used in this session
    used_ids = select(Turn.question_id).where(Turn.session_id == session_id)
    q = q.where(Question.id.not_in(used_ids))

    result = await db.execute(q)
    candidates = result.scalars().all()
    if not candidates:
        return None

    # Get historical mean scores per question
    scores_result = await db.execute(
        select(Turn.question_id, Turn.scores)
        .where(
            Turn.question_id.in_([c.id for c in candidates]),
            Turn.status == "graded",
        )
    )
    score_rows = scores_result.all()

    question_scores: dict[uuid.UUID, list[float]] = {}
    for row in score_rows:
        if row.scores:
            vals = list(row.scores.values())
            question_scores.setdefault(row.question_id, []).append(sum(vals) / len(vals))

    def weight(q: Question) -> float:
        scores = question_scores.get(q.id, [])
        mean = sum(scores) / len(scores) if scores else None
        # Never attempted = high weight; low score = high weight
        if mean is None:
            return 2.0
        return 1.0 / max(mean + 0.1, 0.1)

    weights = [weight(c) for c in candidates]
    total = sum(weights)
    probs = [w / total for w in weights]

    return random.choices(candidates, weights=probs, k=1)[0]


async def _make_turn(db: AsyncSession, session: Session, question: Question, ordinal: int, is_follow_up: bool = False, parent_turn_id: uuid.UUID | None = None) -> Turn:
    turn = Turn(
        session_id=session.id,
        question_id=question.id,
        ordinal=ordinal,
        status="pending",
        is_follow_up=is_follow_up,
        parent_turn_id=parent_turn_id,
        asked_at=datetime.now(timezone.utc),
    )
    db.add(turn)
    await db.commit()
    await db.refresh(turn)
    return turn


async def _turn_with_audio(question: Question, turn: Turn) -> dict:
    """Build the next-turn response with TTS audio URL."""
    audio_url = None
    voice = settings.piper_voice
    try:
        s3_key = await tts_service.synthesize_and_cache(
            str(question.id), question.text, voice, settings.prompt_version
        )
        question.tts_key = s3_key
        audio_url = await asyncio.to_thread(lambda: tts_service.get_presigned_url(s3_key))
    except Exception:
        pass  # TTS failure is non-fatal

    return {
        "turn_id": str(turn.id),
        "ordinal": turn.ordinal,
        "audio_url": audio_url,
        "question": {
            "id": str(question.id),
            "text": question.text,
            "why_asked": question.why_asked,
            "category": question.category,
            "difficulty": question.difficulty,
            "expected_shape": question.expected_shape,
            "source_refs": question.source_refs,
            "follow_ups": question.follow_ups,
            "model_answer": question.model_answer,
            "rubric": question.rubric,
        },
    }


@router.get("")
async def list_sessions(document_id: uuid.UUID | None = None, db: AsyncSession = Depends(get_db)):
    q = select(Session).order_by(Session.started_at.desc())
    if document_id:
        q = q.where(Session.document_id == document_id)
    sessions = (await db.execute(q)).scalars().all()
    if not sessions:
        return []

    turns_result = await db.execute(
        select(Turn.session_id, Turn.status, Turn.scores).where(
            Turn.session_id.in_([s.id for s in sessions])
        )
    )
    by_session: dict[uuid.UUID, list] = {}
    for row in turns_result:
        by_session.setdefault(row.session_id, []).append(row)

    out = []
    for s in sessions:
        turns = by_session.get(s.id, [])
        graded = [t for t in turns if t.status == "graded" and t.scores]
        means = [sum(t.scores.values()) / len(t.scores.values()) for t in graded]
        out.append({
            "id": str(s.id),
            "document_id": str(s.document_id),
            "mode": s.mode,
            "started_at": s.started_at.isoformat(),
            "ended_at": s.ended_at.isoformat() if s.ended_at else None,
            "question_count": len(turns),
            "graded_count": len(graded),
            "mean_score": round(sum(means) / len(means), 2) if means else None,
        })
    return out


@router.post("", response_model=SessionOut)
async def create_session(body: SessionCreate, db: AsyncSession = Depends(get_db)):
    session = Session(
        document_id=body.document_id,
        mode=body.mode,
        config=body.config,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


@router.get("/{session_id}", response_model=SessionOut)
async def get_session(session_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(404, "Sesjon ikke funnet.")
    return session


@router.get("/{session_id}/next")
async def next_turn(session_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(404, "Sesjon ikke funnet.")

    if session.ended_at:
        return {"status": "done"}

    # Count turns so far
    count_result = await db.execute(
        select(func.count(Turn.id)).where(Turn.session_id == session_id)
    )
    turn_count = count_result.scalar() or 0

    # Check config limit
    max_q = session.config.get("count", 20)
    if turn_count >= max_q:
        return {"status": "done"}

    question = await _weighted_draw(db, session.document_id, session_id, session.config)
    if not question:
        return {"status": "done"}

    turn = await _make_turn(db, session, question, ordinal=turn_count)
    return await _turn_with_audio(question, turn)


@router.post("/{session_id}/end")
async def end_session(session_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(404, "Sesjon ikke funnet.")

    session.ended_at = datetime.now(timezone.utc)
    await db.commit()

    # For exam mode, enqueue deferred grading
    if session.mode == "exam":
        redis = await create_pool(RedisSettings.from_dsn(settings.redis_url))
        try:
            await redis.enqueue_job("grade_session", session_id=str(session_id))
        finally:
            await redis.aclose()

    return {"status": "ended", "session_id": str(session_id)}


@router.get("/{session_id}/report")
async def session_report(session_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(404, "Sesjon ikke funnet.")

    turns_result = await db.execute(
        select(Turn, Question)
        .join(Question, Question.id == Turn.question_id)
        .where(Turn.session_id == session_id)
        .order_by(Turn.ordinal)
    )
    rows = turns_result.all()

    turn_data = []
    for turn, question in rows:
        scores_vals = list(turn.scores.values()) if turn.scores else []
        mean_score = sum(scores_vals) / len(scores_vals) if scores_vals else None
        turn_data.append({
            "turn_id": str(turn.id),
            "ordinal": turn.ordinal,
            "status": turn.status,
            "question": {
                "id": str(question.id),
                "text": question.text,
                "category": question.category,
                "difficulty": question.difficulty,
            },
            "transcript": turn.transcript,
            "scores": turn.scores,
            "mean_score": round(mean_score, 2) if mean_score is not None else None,
            "feedback_md": turn.feedback_md,
            "bluffed": turn.bluffed,
            "used_shape": turn.used_shape,
            "missed_points": turn.missed_points,
            "wpm": turn.wpm,
            "duration_ms": turn.duration_ms,
            "filler_count": turn.filler_count,
        })

    # Sort by mean_score ascending (worst first)
    graded = [t for t in turn_data if t["mean_score"] is not None]
    graded_sorted = sorted(graded, key=lambda x: x["mean_score"])

    all_scores = [t["mean_score"] for t in graded if t["mean_score"] is not None]
    return {
        "session_id": str(session_id),
        "mode": session.mode,
        "started_at": session.started_at.isoformat(),
        "ended_at": session.ended_at.isoformat() if session.ended_at else None,
        "total_questions": len(rows),
        "graded_questions": len(graded),
        "mean_score": round(sum(all_scores) / len(all_scores), 2) if all_scores else None,
        "turns": graded_sorted + [t for t in turn_data if t["mean_score"] is None],
    }
