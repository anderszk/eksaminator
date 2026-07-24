"""TTS service — Piper wrapper.

GET  /voices        → list downloaded voices
POST /synthesize    { text, voice? } → audio/wav
"""
import io
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import Response
from pydantic import BaseModel

PIPER_VOICE = os.environ.get("PIPER_VOICE", "nb_NO-talesyntese-medium")
VOICES_DIR = Path("/voices")

app = FastAPI(title="TTS Service")


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

    model_path = VOICES_DIR / f"{req.voice}.onnx"
    config_path = VOICES_DIR / f"{req.voice}.onnx.json"

    voice = PiperVoice.load(str(model_path), config_path=str(config_path))

    buf = io.BytesIO()
    import wave
    with wave.open(buf, "wb") as wav_file:
        voice.synthesize(req.text, wav_file)

    return Response(content=buf.getvalue(), media_type="audio/wav")
