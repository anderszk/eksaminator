"""STT service — FastAPI wrapper over faster-whisper with NB-Whisper model.

Contract (spec §8.5):
  POST /transcribe
    multipart: file=<audio>, language=no, initial_prompt=<glossary terms>
    → 200 { text, segments, avg_logprob, duration_s }

The model is loaded once at startup and held in memory.
Single worker, single concurrency — one user, queuing is fine.
"""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, Form, UploadFile

WHISPER_MODEL = os.environ.get("WHISPER_MODEL", "NbAiLab/nb-whisper-medium")
WHISPER_DEVICE = os.environ.get("WHISPER_DEVICE", "cpu")
WHISPER_COMPUTE = os.environ.get("WHISPER_COMPUTE", "int8")

model = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global model
    from faster_whisper import WhisperModel
    model = WhisperModel(WHISPER_MODEL, device=WHISPER_DEVICE, compute_type=WHISPER_COMPUTE)
    yield


app = FastAPI(title="STT Service", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok", "model": WHISPER_MODEL}


@app.post("/transcribe")
async def transcribe(
    file: UploadFile = File(...),
    language: str = Form("no"),
    initial_prompt: str = Form(""),
):
    audio_bytes = await file.read()

    import io
    segments, info = model.transcribe(
        io.BytesIO(audio_bytes),
        language=language,
        initial_prompt=initial_prompt or None,
        vad_filter=True,
    )

    segs = []
    full_text_parts = []
    avg_logprob_sum = 0.0

    for seg in segments:
        segs.append({
            "start": seg.start,
            "end": seg.end,
            "text": seg.text,
            "avg_logprob": seg.avg_logprob,
        })
        full_text_parts.append(seg.text)
        avg_logprob_sum += seg.avg_logprob

    avg_logprob = avg_logprob_sum / len(segs) if segs else 0.0

    return {
        "text": "".join(full_text_parts).strip(),
        "segments": segs,
        "avg_logprob": avg_logprob,
        "duration_s": info.duration,
    }
