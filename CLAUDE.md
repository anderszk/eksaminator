# Eksaminator

Masteroppgave Defence Trainer — single-user, locally hosted, Docker Compose.

## Stack

- **web/** — Next.js 15 App Router + TypeScript + Tailwind v4
- **api/** — FastAPI + SQLAlchemy (async) + Alembic + arq worker
- **stt/** — NB-Whisper via faster-whisper (FastAPI wrapper)
- **tts/** — Piper TTS (FastAPI wrapper)
- **postgres** — pgvector/pgvector:pg16
- **redis** — arq queue broker only
- **minio** — audio blob storage (S3-compatible)

## Dev

```bash
cp .env.example .env          # fill in ANTHROPIC_API_KEY
make up                       # starts all services
make migrate                  # run Alembic migrations
```

API at http://localhost:8000, web at http://localhost:3000, MinIO console at http://localhost:9090.

## Key patterns

- `api/app/config.py` — all env vars via pydantic-settings, never `os.getenv` elsewhere
- `api/app/db.py` — async SQLAlchemy engine + `get_db` dependency
- `api/app/models/models.py` — all SQLAlchemy models (maps to §6 of the spec)
- `api/alembic/` — Alembic migrations (async env); run with `make migrate`
- `api/app/worker/` — arq worker; runs as a separate container
- `api/app/prompts/` — LLM prompt templates (Markdown), one file per pipeline stage
- `web/lib/nb.ts` — all Norwegian UI strings, never inline

## Routes (Norwegian nav)

| Route | Label |
|---|---|
| `/opplasting` | Last opp |
| `/bibliotek/[docId]` | Bibliotek |
| `/trening/[sessionId]` | Trening |
| `/eksamen/[sessionId]` | Eksamen |
| `/oversikt` | Oversikt |

## Migrations

```bash
# Create a new migration (from inside api/ or via docker exec)
alembic revision --autogenerate -m "description"
make migrate
```

## Spec

See `EKSAMINATOR_SPEC.md` for the full technical specification.
