# Eksaminator

A locally hosted tool for practicing your master's thesis defence. Upload your thesis PDF and simulate a full oral examination — the system analyzes your work, generates examiner-style questions, and lets you answer them aloud with real-time feedback.

## What it does

1. **Analyze your thesis** — extracts key claims, identifies knowledge gaps, and summarizes each section using Claude (Anthropic).
2. **Generate questions** — produces a bank of defence-style questions across 14 categories (motivation, methodology, validity, statistics, ethics, etc.) at four difficulty levels, modeled on how examiners actually question lab-based health science theses.
3. **Simulate the defence** — you answer questions aloud. Norwegian speech recognition (NB-Whisper) transcribes your answer, and the LLM grades it and gives structured feedback.
4. **Track your progress** — an overview page shows which question categories and difficulty levels you have covered and where you are weakest.

Everything runs locally. No data leaves your machine except the LLM calls to Anthropic.


## Quick start

```bash
git clone <repo>
cd eksaminator

cp .env.example .env

make up        # builds and starts all services (~5 min on first run)
make migrate   # runs database migrations
```

Then open [http://localhost:3000](http://localhost:3000) and go to **Last opp** to upload your thesis PDF.

## Services

| Service | URL | Purpose |
|---|---|---|
| Web (Next.js) | http://localhost:3000 | User interface |
| API (FastAPI) | http://localhost:8000 | Backend + REST API |
| MinIO console | http://localhost:9090 | Audio blob storage (admin) |

MinIO credentials: `minioadmin` / `minioadmin` (local only).

## Architecture

```
web (Next.js 15)
    │  REST + SSE
api (FastAPI)
    ├── postgres (pgvector) — thesis data, questions, sessions
    ├── redis               — job queue
    ├── minio               — audio recordings
    ├── stt (NB-Whisper)    — Norwegian speech-to-text
    ├── tts (Piper)         — Norwegian text-to-speech
    └── worker (arq)        — async pipeline stages → Anthropic API
```

The pipeline (ingest → chunk → embed → analyze → generate questions) runs in a background worker so the UI stays responsive during the multi-minute processing.


## Configuration

All options are set in `.env`. The most important ones:

| Variable | Default | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | — | **Required.** Your Anthropic API key |
| `WHISPER_MODEL` | `NbAiLab/nb-whisper-medium` | NB-Whisper model size (`small`, `medium`, `large`) |
| `WHISPER_DEVICE` | `cpu` | `cpu` or `cuda` |
| `PIPER_VOICE` | `nb_NO-talesyntese-medium` | Piper TTS voice |

## Common commands

```bash
make up          # start all services
make down        # stop all services
make migrate     # run pending Alembic migrations
make logs        # tail all service logs
```

## Navigation

| Route | Page |
|---|---|
| `/opplasting` | Upload thesis |
| `/bibliotek` | Document library |
| `/trening` | Practice mode |
| `/eksamen` | Exam simulation |
| `/oversikt` | Progress overview |

## Notes on question generation

Questions are generated across 14 categories matching how Norwegian pharmacy/health science examiners actually probe a defence: method integrity, statistical design, validity and bias, clinical relevance, ethics (REK/personvern), and the fundamentals beneath the method. Difficulty runs from tier 1 (recall) to tier 4 (defend under a challenged premise). The system explicitly targets the full category × difficulty grid to avoid the model's natural bias toward easy recall questions.
