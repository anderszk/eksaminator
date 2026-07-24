import uuid

from fastapi import APIRouter

from app.schemas.schemas import SessionCreate, SessionOut

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", response_model=SessionOut)
async def create_session(body: SessionCreate):
    raise NotImplementedError


@router.get("/{session_id}", response_model=SessionOut)
async def get_session(session_id: uuid.UUID):
    raise NotImplementedError


@router.get("/{session_id}/next")
async def next_turn(session_id: uuid.UUID):
    raise NotImplementedError


@router.post("/{session_id}/end")
async def end_session(session_id: uuid.UUID):
    raise NotImplementedError


@router.get("/{session_id}/report")
async def session_report(session_id: uuid.UUID):
    raise NotImplementedError
