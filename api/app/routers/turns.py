import uuid

from fastapi import APIRouter, UploadFile
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/turns", tags=["turns"])


@router.post("/{turn_id}/answer")
async def submit_answer(turn_id: uuid.UUID, audio: UploadFile):
    raise NotImplementedError


@router.get("/{turn_id}")
async def get_turn(turn_id: uuid.UUID):
    raise NotImplementedError


@router.get("/{turn_id}/grade/stream")
async def grade_stream(turn_id: uuid.UUID) -> StreamingResponse:
    # SSE stream for drill mode grading
    raise NotImplementedError


@router.post("/{turn_id}/follow-up")
async def follow_up(turn_id: uuid.UUID):
    raise NotImplementedError


@router.post("/{turn_id}/skip")
async def skip_turn(turn_id: uuid.UUID):
    raise NotImplementedError
