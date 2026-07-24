import uuid


async def run_pipeline_stage(ctx, *, doc_id: str, stage: str, force: bool = False):
    """Execute one pipeline stage for a document. Idempotent on cache key."""
    raise NotImplementedError


async def grade_turn(ctx, *, turn_id: str):
    """Transcribe + grade a single turn (drill mode)."""
    raise NotImplementedError


async def grade_session(ctx, *, session_id: str):
    """Transcribe + grade all turns in a completed exam session (deferred)."""
    raise NotImplementedError
