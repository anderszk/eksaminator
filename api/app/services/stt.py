"""HTTP client for the STT (NB-Whisper) container."""
import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


async def transcribe(audio_bytes: bytes, glossary: list[str] | None = None) -> dict:
    """POST audio to the STT service. Returns {text, segments, avg_logprob, duration_s}."""
    initial_prompt = ", ".join(glossary) if glossary else ""

    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            f"{settings.stt_url}/transcribe",
            files={"file": ("answer.webm", audio_bytes, "audio/webm")},
            data={"language": "no", "initial_prompt": initial_prompt},
        )
        resp.raise_for_status()
        return resp.json()
