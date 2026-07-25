"""TTS service — Piper wrapper.

GET  /voices        → list downloaded voices
POST /synthesize    { text, voice? } → audio/wav
"""
import io
import logging
import os
import urllib.request
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

logger = logging.getLogger(__name__)

PIPER_VOICE = os.environ.get("PIPER_VOICE", "no_NO-talesyntese-medium")
VOICES_DIR = Path("/voices")

# rhasspy/piper-voices layout: {lang}/{locale}/{name}/{quality}/{locale}-{name}-{quality}.onnx[.json]
VOICES_BASE_URL = "https://huggingface.co/rhasspy/piper-voices/resolve/main"


def _voice_repo_path(voice: str) -> str:
    locale, name, quality = voice.split("-", 2)
    lang = locale.split("_")[0]
    return f"{lang}/{locale}/{name}/{quality}/{voice}"


def _ensure_voice(voice: str) -> None:
    """Download the voice's .onnx + .onnx.json into VOICES_DIR if not already there."""
    model_path = VOICES_DIR / f"{voice}.onnx"
    config_path = VOICES_DIR / f"{voice}.onnx.json"
    if model_path.exists() and config_path.exists():
        return

    VOICES_DIR.mkdir(parents=True, exist_ok=True)
    repo_path = _voice_repo_path(voice)
    for suffix, dest in ((".onnx", model_path), (".onnx.json", config_path)):
        if dest.exists():
            continue
        url = f"{VOICES_BASE_URL}/{repo_path}{suffix}"
        logger.info("Downloading Piper voice file: %s -> %s", url, dest)
        tmp = dest.with_suffix(dest.suffix + ".part")
        urllib.request.urlretrieve(url, tmp)
        tmp.rename(dest)


@asynccontextmanager
async def lifespan(app: FastAPI):
    import asyncio
    try:
        await asyncio.to_thread(_ensure_voice, PIPER_VOICE)
    except Exception:
        logger.exception("Failed to download default Piper voice %s at startup", PIPER_VOICE)
    yield


app = FastAPI(title="TTS Service", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok", "default_voice": PIPER_VOICE}


@app.get("/voices")
async def list_voices():
    return {"voices": [p.stem for p in VOICES_DIR.glob("*.onnx")]}


class SynthesizeRequest(BaseModel):
    text: str
    voice: str = PIPER_VOICE


@app.post("/synthesize")
async def synthesize(req: SynthesizeRequest):
    from piper import PiperVoice

    try:
        _ensure_voice(req.voice)
    except Exception as exc:
        raise HTTPException(502, f"Kunne ikke hente stemmemodell «{req.voice}»: {exc}") from exc

    model_path = VOICES_DIR / f"{req.voice}.onnx"
    config_path = VOICES_DIR / f"{req.voice}.onnx.json"

    voice = PiperVoice.load(str(model_path), config_path=str(config_path))

    # PiperVoice.synthesize() returns an iterable of AudioChunk (one per sentence),
    # not a writer over a wave file — each chunk carries its own format info, which
    # is constant across chunks for a given voice.
    chunks = list(voice.synthesize(req.text))
    if not chunks:
        raise HTTPException(422, "Ingen lyd generert for teksten.")

    buf = io.BytesIO()
    import wave
    with wave.open(buf, "wb") as wav_file:
        wav_file.setnchannels(chunks[0].sample_channels)
        wav_file.setsampwidth(chunks[0].sample_width)
        wav_file.setframerate(chunks[0].sample_rate)
        for chunk in chunks:
            wav_file.writeframes(chunk.audio_int16_bytes)

    return Response(content=buf.getvalue(), media_type="audio/wav")
