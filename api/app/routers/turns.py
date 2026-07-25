import asyncio
import json
import uuid
from datetime import datetime, timezone

import boto3
from arq import create_pool
from arq.connections import RedisSettings
from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_db
from app.models.models import Question, Session, Turn

router = APIRouter(prefix="/turns", tags=["turns"])


class TextAnswerIn(BaseModel):
    text: str


def _s3():
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name="us-east-1",
    )


@router.post("/{turn_id}/answer")
async def submit_answer(turn_id: uuid.UUID, audio: UploadFile, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Turn).where(Turn.id == turn_id))
    turn = result.scalar_one_or_none()
    if not turn:
        raise HTTPException(404, "Turn ikke funnet.")

    audio_bytes = await audio.read()
    s3_key = f"answers/{turn_id}.webm"

    await asyncio.to_thread(
        lambda: _s3().put_object(
            Bucket=settings.s3_bucket,
            Key=s3_key,
            Body=audio_bytes,
            ContentType="audio/webm",
        )
    )

    turn.answer_s3_key = s3_key
    turn.answered_at = datetime.now(timezone.utc)
    turn.status = "recorded"
    await db.commit()

    # Get session mode
    session_result = await db.execute(select(Session).where(Session.id == turn.session_id))
    session = session_result.scalar_one_or_none()

    if session and session.mode == "drill":
        redis = await create_pool(RedisSettings.from_dsn(settings.redis_url))
        try:
            await redis.enqueue_job("grade_turn", turn_id=str(turn_id))
        finally:
            await redis.aclose()

    return {"status": "recorded", "turn_id": str(turn_id)}


@router.post("/{turn_id}/answer-text")
async def submit_text_answer(turn_id: uuid.UUID, body: TextAnswerIn, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Turn).where(Turn.id == turn_id))
    turn = result.scalar_one_or_none()
    if not turn:
        raise HTTPException(404, "Turn ikke funnet.")

    text = body.text.strip()
    if not text:
        raise HTTPException(400, "Svaret kan ikke være tomt.")

    # No audio, so no STT — grade_turn skips straight to grading when it sees
    # a transcript already set with no answer_s3_key (see worker/stages.py).
    turn.transcript = text
    turn.answered_at = datetime.now(timezone.utc)
    turn.status = "recorded"
    await db.commit()

    session_result = await db.execute(select(Session).where(Session.id == turn.session_id))
    session = session_result.scalar_one_or_none()

    if session and session.mode == "drill":
        redis = await create_pool(RedisSettings.from_dsn(settings.redis_url))
        try:
            await redis.enqueue_job("grade_turn", turn_id=str(turn_id))
        finally:
            await redis.aclose()

    return {"status": "recorded", "turn_id": str(turn_id)}


@router.get("/{turn_id}")
async def get_turn(turn_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Turn).where(Turn.id == turn_id))
    turn = result.scalar_one_or_none()
    if not turn:
        raise HTTPException(404, "Turn ikke funnet.")
    return {
        "id": str(turn.id),
        "session_id": str(turn.session_id),
        "question_id": str(turn.question_id),
        "ordinal": turn.ordinal,
        "status": turn.status,
        "transcript": turn.transcript,
        "stt_confidence": turn.stt_confidence,
        "scores": turn.scores,
        "bluffed": turn.bluffed,
        "used_shape": turn.used_shape,
        "missed_points": turn.missed_points,
        "feedback_md": turn.feedback_md,
        "wpm": turn.wpm,
        "duration_ms": turn.duration_ms,
        "filler_count": turn.filler_count,
        "filler_rate": turn.filler_rate,
        "longest_pause_ms": turn.longest_pause_ms,
        "time_to_first_word_ms": turn.time_to_first_word_ms,
        "asked_at": turn.asked_at.isoformat() if turn.asked_at else None,
        "answered_at": turn.answered_at.isoformat() if turn.answered_at else None,
        "graded_at": turn.graded_at.isoformat() if turn.graded_at else None,
    }


@router.get("/{turn_id}/grade/stream")
async def grade_stream(turn_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """SSE stream: polls until turn is graded, then streams result."""

    async def event_generator():
        from app.db import SessionLocal

        for attempt in range(120):  # poll up to 2 minutes
            await asyncio.sleep(1)
            async with SessionLocal() as poll_db:
                result = await poll_db.execute(select(Turn).where(Turn.id == turn_id))
                turn = result.scalar_one_or_none()
                if not turn:
                    yield f"data: {json.dumps({'type': 'error', 'message': 'not found'})}\n\n"
                    return

                if turn.transcript and attempt < 5:
                    # Send transcript as soon as available
                    yield f"data: {json.dumps({'type': 'transcript', 'text': turn.transcript, 'stt_confidence': turn.stt_confidence})}\n\n"

                if turn.status == "graded":
                    yield f"data: {json.dumps({'type': 'grade', 'scores': turn.scores, 'feedback_md': turn.feedback_md, 'bluffed': turn.bluffed, 'used_shape': turn.used_shape, 'missed_points': turn.missed_points or [], 'duration_ms': turn.duration_ms, 'wpm': turn.wpm, 'filler_count': turn.filler_count, 'longest_pause_ms': turn.longest_pause_ms})}\n\n"
                    return

                if turn.status in ("skipped",):
                    yield f"data: {json.dumps({'type': 'skipped'})}\n\n"
                    return

        yield f"data: {json.dumps({'type': 'timeout'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/{turn_id}/skip")
async def skip_turn(turn_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Turn).where(Turn.id == turn_id))
    turn = result.scalar_one_or_none()
    if not turn:
        raise HTTPException(404, "Turn ikke funnet.")
    turn.status = "skipped"
    await db.commit()
    return {"status": "skipped"}


@router.post("/{turn_id}/follow-up")
async def follow_up(turn_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    from app.models.models import Session as SessionModel
    from app.services import tts as tts_service
    from sqlalchemy import func

    result = await db.execute(select(Turn).where(Turn.id == turn_id))
    parent_turn = result.scalar_one_or_none()
    if not parent_turn:
        raise HTTPException(404, "Turn ikke funnet.")

    q_result = await db.execute(select(Question).where(Question.id == parent_turn.question_id))
    parent_question = q_result.scalar_one_or_none()
    if not parent_question:
        raise HTTPException(404, "Spørsmål ikke funnet.")

    follow_ups = parent_question.follow_ups or []
    if not follow_ups:
        raise HTTPException(400, "Ingen oppfølgingsspørsmål tilgjengelig.")

    # Pick the first follow-up text, or random if multiple
    import random
    follow_up_text = random.choice(follow_ups) if isinstance(follow_ups, list) else str(follow_ups)

    # Count existing turns
    count_result = await db.execute(
        select(func.count(Turn.id)).where(Turn.session_id == parent_turn.session_id)
    )
    ordinal = count_result.scalar() or 0

    # We need a question for the follow-up — reuse the parent question but with modified text
    # Create a synthetic turn pointing to the same question
    new_turn = Turn(
        session_id=parent_turn.session_id,
        question_id=parent_question.id,
        ordinal=ordinal,
        status="pending",
        is_follow_up=True,
        parent_turn_id=parent_turn.id,
        asked_at=datetime.now(timezone.utc),
    )
    db.add(new_turn)
    await db.commit()
    await db.refresh(new_turn)

    # Generate audio for follow-up text
    audio_url = None
    try:
        s3_key = await tts_service.synthesize_and_cache(
            f"{parent_turn.id}_fu_{ordinal}",
            follow_up_text,
            settings.piper_voice,
            settings.prompt_version,
        )
        audio_url = await asyncio.to_thread(lambda: tts_service.get_presigned_url(s3_key))
    except Exception:
        pass

    return {
        "turn_id": str(new_turn.id),
        "ordinal": ordinal,
        "audio_url": audio_url,
        "question": {
            "id": str(parent_question.id),
            "text": follow_up_text,
            "why_asked": parent_question.why_asked,
            "category": parent_question.category,
            "difficulty": min(parent_question.difficulty + 1, 4),
            "expected_shape": parent_question.expected_shape,
            "source_refs": parent_question.source_refs,
            "follow_ups": [],
            "model_answer": None,
            "rubric": parent_question.rubric,
        },
    }
