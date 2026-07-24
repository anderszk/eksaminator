# Masteroppgave Defence Trainer — Technical Specification

**Version** 1.0
**Document language** English · **Application language** Norwegian (bokmål)
**Domain** Pharmacy / medicine / health — laboratory-based master's thesis
**Target** Single-user, locally hosted, Docker Compose. Build window: 2–3 days. Use window: 2 weeks.

---

## 1. Purpose and scope

### 1.1 What this is

A single-user platform that ingests a master's thesis PDF, performs a staged AI analysis of it, and turns that analysis into a **spoken defence simulator**: the examiner asks questions aloud, the candidate answers aloud, and the system transcribes, grades and gives feedback.

### 1.2 The skill being trained

Producing a coherent, 60–90 second, unrehearsed spoken answer about one's own scientific reasoning, in Norwegian, without notes, under mild adversarial pressure.

Everything in this system is subordinate to that. Any feature that does not serve it is out of scope for v1.

### 1.3 Defence format assumed

1. Candidate presents (typically 15–20 min).
2. Examiners question the candidate (typically 30–45 min).
3. Committee: internal sensor (often the supervisor or a department representative) + external sensor.

**The application targets phase 2.** Phase 1 (presentation) gets a single lightweight support feature (§9.5) and nothing more.

### 1.4 Explicit non-goals for v1

| Not building | Why |
|---|---|
| Multi-user auth, orgs, sharing | Single user, localhost |
| Payment, quotas, rate limiting | Not applicable |
| Mobile-responsive layout beyond "doesn't break" | Practice happens at a desk with a microphone |
| Real-time streaming ASR | Chunked upload hits the latency budget adequately (§8.6) |
| Fine-tuning any model | No |
| Slide analysis / PPTX ingest | Out of scope |
| Spaced repetition scheduling | Two-week horizon makes SRS intervals meaningless |

> **Note on SRS:** the original plan included spaced repetition. It is cut. SRS pays off over months. Over 14 days, a simple weakest-first weighted queue (§9.4) outperforms it and costs an hour instead of a day.

---

## 2. Domain model — what makes a lab thesis defence different

This section drives the prompts in §7. It is the highest-value part of the spec and should not be skipped when implementing.

### 2.1 Where examiners actually push, in a wet-lab health science thesis

Question generation must be grounded in a domain-specific vulnerability checklist rather than generic "what are your limitations" prompting. The checklist below is embedded verbatim into the vulnerability-analysis prompt.

**Method and assay integrity**
- Choice of assay/platform vs alternatives; why this and not the standard method in the field
- Positive and negative controls — present? appropriate? what would a missing control invalidate?
- Blanks, baseline correction, background subtraction
- Calibration curve: range, linearity, R², whether samples fell inside the calibrated range
- LOD / LOQ (deteksjonsgrense / kvantifiseringsgrense) — determined how?
- Accuracy vs precision; intra- and inter-assay CV
- Antibody validation, primer specificity, probe design — as applicable
- Cell line authentication, passage number, mycoplasma testing — as applicable
- Sample handling: storage temperature, freeze–thaw cycles, time to processing, stability data
- Buffer composition, pH, ionic strength, incubation times — and sensitivity to them
- Instrument calibration, drift, run order, batch effects

**Design and statistics**
- Sample size and power; was a power calculation performed a priori or is n justified post hoc?
- Technical vs biological replicates — and whether the statistics treated them correctly (a common and heavily punished error)
- Randomisation, blinding, run order
- Statistical test assumptions: normality, variance homogeneity, independence
- Multiple comparisons and correction
- Effect size vs statistical significance; clinical vs statistical relevance
- Outlier handling and its pre-specification
- Missing data

**Interpretation and validity**
- Internal validity: confounders, selection bias, measurement bias
- External validity: in vitro → in vivo, animal → human, healthy volunteers → patients
- Causality vs correlation
- Alternative mechanistic explanations for the observed result
- Dose/concentration relevance — is the concentration used physiologically or clinically achievable?
- Whether the model system actually models the condition claimed

**Regulatory, ethical, translational**
- REK approval, biobank consent, GDPR/personvern for human material
- Animal welfare approval (Mattilsynet / FOTS) if applicable
- GLP/GMP relevance where the work touches product quality
- Data availability and reproducibility; would another lab reproduce this from the methods section as written?
- Clinical or pharmaceutical relevance: what would need to be true for this to matter to a patient?

**Fundamentals beneath the work**
The examiner's classic move: drop one level below the method. Pharmacokinetic principles, receptor binding and affinity, enzyme kinetics, chromatographic separation principles, spectroscopic principle underlying the readout, cell signalling basics, drug formulation and stability, statistics fundamentals. These questions look easy and are the ones candidates most often fumble.

### 2.2 Question taxonomy

Stored as `questions.category`. Norwegian labels are what the UI displays.

| Key | Norwegian label | Notes |
|---|---|---|
| `motivasjon` | Motivasjon og problemstilling | Why this question, why it matters |
| `metodevalg` | Metodevalg | Justification vs alternatives |
| `metodeforstaelse` | Metodeforståelse | Mechanics, assumptions, failure modes |
| `resultater` | Resultater og tolkning | Per figure/table |
| `statistikk` | Statistikk og forsøksdesign | |
| `validitet` | Validitet og feilkilder | Controls, bias, confounders |
| `alternativ` | Alternative forklaringer | Adversarial by nature |
| `litteratur` | Litteratur og posisjonering | |
| `relevans` | Klinisk/farmasøytisk relevans | Translational |
| `etikk` | Etikk og regelverk | REK, personvern, dyrevelferd |
| `reproduserbarhet` | Reproduserbarhet | |
| `grunnlag` | Faglig grunnlag | The level beneath the method |
| `videre` | Videre arbeid | |
| `kritisk` | Kritiske spørsmål | Premise-challenging, hostile framing |

### 2.3 Difficulty tiers

Stored as `questions.difficulty`, integer 1–4.

| Tier | Key | Norwegian | Meaning |
|---|---|---|---|
| 1 | `gjenkalle` | Gjenkalle | State a fact from your own work |
| 2 | `forklare` | Forklare | Explain a mechanism or a choice |
| 3 | `forsvare` | Forsvare | Defend a choice against a named alternative |
| 4 | `motstå` | Motstå | Hold up under a challenged premise |

Generation must fill the full category × difficulty grid. Without an explicit instruction the model produces ~80% tier 1–2, which is the wrong training load.

### 2.4 The three answer shapes

Rehearsed explicitly; the grader is aware of them and names which one the answer should have used.

1. **Direkte** — påstand → belegg → forbehold. *(claim → evidence → boundary condition)*
2. **Utfordre premisset** — anerkjenn → omformuler → forsvar.
3. **Innrømmelse** — innrøm rent → resonner høyt om hvordan du ville angrepet det → stopp.

Shape 3 is the differentiator in a real defence and the one candidates practise least. The grader must never penalise a correct, well-reasoned "det vet jeg ikke" — it should reward it, and penalise bluffing instead (§8.8).

---

## 3. Language decisions

| Surface | Language |
|---|---|
| All UI copy, labels, buttons, empty states, errors | Norwegian bokmål |
| Generated summaries, questions, model answers, feedback | Norwegian bokmål |
| Code, identifiers, comments, DB column names, API paths | English |
| This spec | English |
| Log output | English |

**Terminology:** the thesis is written in either Norwegian or English; scientific terminology should be preserved in whichever form the thesis uses. The generation prompts instruct: write in Norwegian bokmål, but keep established English scientific terms as-is where a Norwegian translation would be unnatural (e.g. *western blot*, *primer*, *assay*, *baseline*). Do not invent Norwegian translations of technical terms.

**Nynorsk:** not supported in v1. NB-Whisper handles nynorsk output, but mixing forms adds no value here.

---

## 4. Architecture

```
┌──────────────────────────────────────────────────────────┐
│  web — Next.js 15 (App Router) + Tailwind                │
│  /opplasting  /bibliotek  /trening  /eksamen  /oversikt  │
└───────────────┬──────────────────────────────────────────┘
                │  REST + SSE (grading stream)
┌───────────────▼──────────────────────────────────────────┐
│  api — FastAPI                                            │
│  ingest · pipeline control · sessions · grading · media   │
└───┬───────────┬───────────┬───────────┬──────────────────┘
    │           │           │           │
┌───▼────┐ ┌────▼────┐ ┌────▼────┐ ┌────▼─────┐
│postgres│ │  redis  │ │  minio  │ │   stt    │
│pgvector│ │  queue  │ │  blobs  │ │NB-Whisper│
└────────┘ └────┬────┘ └─────────┘ └──────────┘
                │
          ┌─────▼──────┐        ┌──────────────┐
          │   worker   │───────▶│  LLM API     │
          │   (arq)    │        │  (Anthropic) │
          └─────┬──────┘        └──────────────┘
                │
          ┌─────▼──────┐
          │    tts     │  (Piper local, or cloud provider)
          └────────────┘
```

### 4.1 Why these boundaries

- **`stt` is its own container.** It carries multi-GB model weights and a slow cold start. Coupling it to `api` makes every backend code change a 3-minute rebuild. Keep `api` a 5-second rebuild.
- **`worker` is separate from `api`.** Pipeline stages take minutes; HTTP requests must not.
- **`minio` rather than filesystem volumes.** Audio blobs get presigned URLs, which means the browser fetches audio directly instead of proxying multi-MB files through FastAPI. Also makes the eventual move to real S3 free.
- **`redis`** is the arq queue broker and nothing else. No caching layer — Postgres is the cache (§6.3).

---

## 5. Infrastructure

### 5.1 Repository layout

```
defence-trainer/
├── docker-compose.yml
├── docker-compose.override.yml      # dev: bind mounts, hot reload
├── .env.example
├── Makefile
├── web/
│   ├── Dockerfile
│   ├── package.json
│   ├── next.config.ts
│   ├── tailwind.config.ts
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx                 # redirect → /bibliotek
│   │   ├── opplasting/
│   │   ├── bibliotek/[docId]/
│   │   ├── trening/[sessionId]/
│   │   ├── eksamen/[sessionId]/
│   │   └── oversikt/
│   ├── components/
│   │   ├── recorder/                # MediaRecorder + VAD + level meter
│   │   ├── examiner/                # question card, TTS player
│   │   ├── feedback/                # score radar, rubric, model answer
│   │   └── ui/
│   └── lib/
│       ├── api.ts                   # typed client
│       ├── vad.ts
│       └── nb.ts                    # Norwegian string table
├── api/
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── alembic/
│   └── app/
│       ├── main.py
│       ├── config.py
│       ├── db.py
│       ├── models/                  # SQLAlchemy
│       ├── schemas/                 # Pydantic
│       ├── routers/
│       │   ├── documents.py
│       │   ├── pipeline.py
│       │   ├── content.py
│       │   ├── sessions.py
│       │   ├── turns.py
│       │   └── media.py
│       ├── services/
│       │   ├── pdf.py               # parse, chunk, page-map
│       │   ├── embeddings.py
│       │   ├── llm.py               # client + retry + cost log
│       │   ├── cache.py             # stage cache key logic
│       │   ├── stt.py
│       │   ├── tts.py
│       │   ├── grading.py
│       │   └── metrics.py           # wpm, fillers, pauses
│       ├── prompts/
│       │   ├── s2_structure.md
│       │   ├── s3_claims.md
│       │   ├── s4_vulnerability.md
│       │   ├── s5_questions.md
│       │   ├── s6_answers.md
│       │   ├── s7_summaries.md
│       │   └── grade_turn.md
│       └── worker/
│           ├── main.py              # arq worker
│           └── stages.py
├── stt/
│   ├── Dockerfile
│   └── server.py                    # FastAPI wrapper over faster-whisper
└── tts/
    ├── Dockerfile
    └── server.py                    # Piper wrapper (if local TTS)
```

### 5.2 docker-compose.yml

```yaml
name: defence-trainer

services:
  web:
    build:
      context: ./web
      target: ${BUILD_TARGET:-dev}
    environment:
      NEXT_PUBLIC_API_URL: http://localhost:8000
    ports: ["3000:3000"]
    depends_on:
      api: { condition: service_healthy }

  api:
    build: ./api
    env_file: .env
    environment:
      DATABASE_URL: postgresql+psycopg://app:app@postgres:5432/defence
      REDIS_URL: redis://redis:6379/0
      S3_ENDPOINT: http://minio:9000
      STT_URL: http://stt:9001
      TTS_URL: http://tts:9002
    ports: ["8000:8000"]
    depends_on:
      postgres: { condition: service_healthy }
      redis:    { condition: service_healthy }
      minio:    { condition: service_healthy }
    healthcheck:
      test: ["CMD", "curl", "-fsS", "http://localhost:8000/health"]
      interval: 10s
      timeout: 3s
      retries: 10
      start_period: 20s

  worker:
    build: ./api
    command: ["arq", "app.worker.main.WorkerSettings"]
    env_file: .env
    environment:
      DATABASE_URL: postgresql+psycopg://app:app@postgres:5432/defence
      REDIS_URL: redis://redis:6379/0
      S3_ENDPOINT: http://minio:9000
      STT_URL: http://stt:9001
      TTS_URL: http://tts:9002
    depends_on:
      postgres: { condition: service_healthy }
      redis:    { condition: service_healthy }

  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: app
      POSTGRES_PASSWORD: app
      POSTGRES_DB: defence
    ports: ["5432:5432"]
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U app -d defence"]
      interval: 5s
      timeout: 3s
      retries: 10

  redis:
    image: redis:7-alpine
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 10

  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9090"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    ports: ["9000:9000", "9090:9090"]
    volumes:
      - miniodata:/data
    healthcheck:
      test: ["CMD", "mc", "ready", "local"]
      interval: 5s
      timeout: 3s
      retries: 10

  stt:
    build: ./stt
    environment:
      WHISPER_MODEL: ${WHISPER_MODEL:-NbAiLab/nb-whisper-medium}
      WHISPER_DEVICE: ${WHISPER_DEVICE:-cpu}
      WHISPER_COMPUTE: ${WHISPER_COMPUTE:-int8}
    volumes:
      - hfcache:/root/.cache/huggingface
    ports: ["9001:9001"]
    # Uncomment on an NVIDIA host:
    # deploy:
    #   resources:
    #     reservations:
    #       devices: [{ driver: nvidia, count: 1, capabilities: [gpu] }]

  tts:
    build: ./tts
    environment:
      PIPER_VOICE: ${PIPER_VOICE:-nb_NO-talesyntese-medium}
    volumes:
      - piperdata:/voices
    ports: ["9002:9002"]

volumes:
  pgdata:
  miniodata:
  hfcache:
  piperdata:
```

### 5.3 .env.example

```bash
# LLM
ANTHROPIC_API_KEY=sk-ant-...
LLM_MODEL=claude-sonnet-4-6
LLM_MAX_TOKENS=8000

# Embeddings — local model, no external call
EMBEDDING_MODEL=intfloat/multilingual-e5-large
EMBEDDING_DIM=1024

# Speech-to-text
WHISPER_MODEL=NbAiLab/nb-whisper-medium
WHISPER_DEVICE=cpu          # cuda if available
WHISPER_COMPUTE=int8        # float16 on GPU

# Text-to-speech
TTS_PROVIDER=piper          # piper | azure
PIPER_VOICE=nb_NO-talesyntese-medium
AZURE_SPEECH_KEY=
AZURE_SPEECH_REGION=norwayeast
AZURE_TTS_VOICE=nb-NO-PernilleNeural

# Storage
S3_BUCKET=defence
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin

# Behaviour
ANSWER_TIME_LIMIT_S=90
VAD_SILENCE_MS=2500
PROMPT_VERSION=v1
```

### 5.4 Speech model selection

**STT — NB-Whisper (Nasjonalbiblioteket).** This is the correct choice and it is not close. NB-Whisper is a Norwegian fine-tune of OpenAI Whisper trained by the National Library of Norway; <cite index="8-1">the published results report Norwegian bokmål word error rate improving over Whisper large-v3 from 10.4 to 6.6 on the Fleurs dataset and from 6.8 to 2.2 on NST</cite>. <cite index="4-1">It is Apache-2.0 licensed, supports bokmål, nynorsk and English, and ships in tiny/base/small/medium/large sizes.</cite>

Practical selection:

| Host | Model | Expected latency for 90 s audio |
|---|---|---|
| CPU only, 8+ cores | `nb-whisper-small` via faster-whisper, int8 | ~15–30 s |
| CPU only, want quality | `nb-whisper-medium`, int8 | ~40–70 s |
| NVIDIA GPU | `nb-whisper-large`, float16 | ~3–6 s |

Run it through **faster-whisper** (CTranslate2), not raw transformers — roughly 4× faster on CPU at the same quality. If you have no GPU, use `small` for Drill mode and let Mock mode transcribe in the background after the session (it defers grading anyway, §8.7).

Domain vocabulary matters here: a pharmacy thesis is full of compound Norwegian technical nouns and English loanwords. Pass an `initial_prompt` to Whisper containing 30–50 domain terms extracted from the thesis (§7 stage 2 emits `glossary[]` for exactly this). This measurably reduces error on the terms you most need transcribed correctly.

**TTS — two supported options.**

- **Piper** (local, free, fast, offline). Norwegian bokmål voices exist via Språkbanken/NB. Quality is "clear synthetic", not human. Adequate: you are training on the *content* of the question, not the examiner's charisma.
- **Cloud neural voice** if you want realism. Azure Speech has nb-NO neural voices — <cite index="12-1">Pernille (female) and Finn (male) are the standard bokmål neural speakers</cite>. Two examiner voices makes the simulation noticeably better; assign one voice per simulated examiner persona (§9.3).

Verify current voice availability and pricing at build time; this landscape moves.

**TTS caching is mandatory.** Question audio is generated once per (question_id, voice, prompt_version) and stored in MinIO forever. You will hear the same questions dozens of times.

---

## 6. Data model

### 6.1 Extensions and enums

```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TYPE pipeline_stage AS ENUM (
  'ingest','structure','claims','vulnerabilities','questions','answers','summaries'
);
CREATE TYPE run_status AS ENUM ('pending','running','done','failed','stale');
CREATE TYPE session_mode AS ENUM ('drill','exam');
CREATE TYPE turn_status AS ENUM ('pending','recorded','transcribed','graded','skipped');
```

### 6.2 Tables

```sql
-- ─────────────────────────────── documents

CREATE TABLE documents (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  filename      text NOT NULL,
  sha256        text NOT NULL UNIQUE,
  page_count    int  NOT NULL,
  char_count    int  NOT NULL,
  language      text NOT NULL DEFAULT 'no',
  s3_key        text NOT NULL,
  title         text,
  uploaded_at   timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE chunks (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id   uuid NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  ordinal       int  NOT NULL,
  page_start    int  NOT NULL,
  page_end      int  NOT NULL,
  section_path  text,                    -- "4. Resultater > 4.2 HPLC-analyse"
  kind          text NOT NULL DEFAULT 'text',  -- text | table | figure_caption | reference
  text          text NOT NULL,
  token_count   int  NOT NULL,
  embedding     vector(1024),
  UNIQUE (document_id, ordinal)
);

CREATE INDEX chunks_doc_idx  ON chunks (document_id, ordinal);
CREATE INDEX chunks_vec_idx  ON chunks USING hnsw (embedding vector_cosine_ops);
CREATE INDEX chunks_fts_idx  ON chunks USING gin (to_tsvector('norwegian', text));

-- ─────────────────────────────── pipeline

CREATE TABLE analysis_runs (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id     uuid NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  stage           pipeline_stage NOT NULL,
  cache_key       text NOT NULL,
  prompt_version  text NOT NULL,
  model           text NOT NULL,
  params_hash     text NOT NULL,
  status          run_status NOT NULL DEFAULT 'pending',
  input_tokens    int DEFAULT 0,
  output_tokens   int DEFAULT 0,
  cost_usd        numeric(10,4) DEFAULT 0,
  duration_ms     int,
  error           text,
  output          jsonb,
  created_at      timestamptz NOT NULL DEFAULT now(),
  completed_at    timestamptz
);

CREATE UNIQUE INDEX analysis_runs_cache_idx
  ON analysis_runs (cache_key) WHERE status = 'done';
CREATE INDEX analysis_runs_doc_stage_idx
  ON analysis_runs (document_id, stage, created_at DESC);

-- ─────────────────────────────── derived content

CREATE TABLE thesis_map (
  run_id        uuid PRIMARY KEY REFERENCES analysis_runs(id) ON DELETE CASCADE,
  document_id   uuid NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  data          jsonb NOT NULL         -- schema in §7.2
);

CREATE TABLE claims (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id        uuid NOT NULL REFERENCES analysis_runs(id) ON DELETE CASCADE,
  document_id   uuid NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  text          text NOT NULL,
  claim_type    text NOT NULL,          -- empirisk | metodisk | tolkning | teoretisk
  evidence_refs jsonb NOT NULL,         -- [{chunk_id, page, quote_hint}]
  strength      int  NOT NULL CHECK (strength BETWEEN 1 AND 5),
  created_at    timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE vulnerabilities (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id        uuid NOT NULL REFERENCES analysis_runs(id) ON DELETE CASCADE,
  claim_id      uuid REFERENCES claims(id) ON DELETE CASCADE,
  document_id   uuid NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  checklist_key text NOT NULL,          -- e.g. 'kontroller', 'teknisk_vs_biologisk_replikat'
  description   text NOT NULL,
  severity      int  NOT NULL CHECK (severity BETWEEN 1 AND 5),
  attack_angle  text NOT NULL,          -- how an examiner would phrase the push
  best_defence  text                    -- the honest strongest response
);

CREATE TABLE questions (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id         uuid NOT NULL REFERENCES analysis_runs(id) ON DELETE CASCADE,
  document_id    uuid NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  claim_id       uuid REFERENCES claims(id) ON DELETE SET NULL,
  vulnerability_id uuid REFERENCES vulnerabilities(id) ON DELETE SET NULL,
  category       text NOT NULL,
  difficulty     int  NOT NULL CHECK (difficulty BETWEEN 1 AND 4),
  text           text NOT NULL,          -- Norwegian
  why_asked      text NOT NULL,          -- Norwegian, shown after answering
  expected_shape text NOT NULL,          -- direkte | utfordre | innrommelse
  source_refs    jsonb NOT NULL,         -- [{page, section_path, chunk_id}]
  follow_ups     jsonb DEFAULT '[]',     -- ["...", "..."] escalation prompts
  model_answer   text,                    -- Norwegian, ~120 words
  rubric         jsonb,                   -- schema in §8.8
  tts_key        text,                    -- MinIO key of cached question audio
  retired        boolean NOT NULL DEFAULT false,
  created_at     timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX questions_doc_idx  ON questions (document_id, category, difficulty);

CREATE TABLE summaries (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id       uuid NOT NULL REFERENCES analysis_runs(id) ON DELETE CASCADE,
  document_id  uuid NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  scope        text NOT NULL,            -- 'chapter' | 'concept' | 'figure' | 'spine'
  ref          text NOT NULL,            -- chapter number, concept name, figure id
  title        text NOT NULL,
  body_md      text NOT NULL,            -- Norwegian markdown
  source_refs  jsonb NOT NULL,
  ordinal      int NOT NULL DEFAULT 0
);

-- ─────────────────────────────── practice

CREATE TABLE sessions (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id  uuid NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  mode         session_mode NOT NULL,
  config       jsonb NOT NULL DEFAULT '{}',   -- categories, difficulty, count, voice, examiner
  started_at   timestamptz NOT NULL DEFAULT now(),
  ended_at     timestamptz,
  summary      jsonb                           -- aggregate scores, written at end
);

CREATE TABLE turns (
  id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id         uuid NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
  question_id        uuid NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
  ordinal            int  NOT NULL,
  status             turn_status NOT NULL DEFAULT 'pending',
  is_follow_up       boolean NOT NULL DEFAULT false,
  parent_turn_id     uuid REFERENCES turns(id) ON DELETE SET NULL,

  answer_s3_key      text,
  transcript         text,
  stt_confidence     real,

  duration_ms        int,
  wpm                real,
  filler_count       int,
  filler_rate        real,
  longest_pause_ms   int,
  time_to_first_word_ms int,

  scores             jsonb,               -- {korrekthet, begrunnelse, forbehold, struktur}
  bluffed            boolean,
  used_shape         text,
  feedback_md        text,
  missed_points      jsonb,               -- ["...","..."]

  asked_at           timestamptz,
  answered_at        timestamptz,
  graded_at          timestamptz,
  UNIQUE (session_id, ordinal)
);

CREATE INDEX turns_question_idx ON turns (question_id, graded_at DESC);

-- ─────────────────────────────── planning

CREATE TABLE plan_items (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id  uuid REFERENCES documents(id) ON DELETE CASCADE,
  day          int  NOT NULL CHECK (day BETWEEN 1 AND 14),
  title        text NOT NULL,            -- Norwegian
  detail_md    text,
  minutes      int,
  kind         text NOT NULL,            -- lesing | analyse | muntlig | mock | hvile
  done         boolean NOT NULL DEFAULT false,
  linked_categories text[] DEFAULT '{}',
  ordinal      int NOT NULL DEFAULT 0
);
```

### 6.3 Cache key — the mechanism that stops re-analysis

```python
def cache_key(doc_sha: str, stage: str, prompt_version: str,
              model: str, params: dict, upstream_keys: list[str]) -> str:
    payload = json.dumps({
        "doc": doc_sha,
        "stage": stage,
        "pv": prompt_version,
        "model": model,
        "params": params,
        "upstream": sorted(upstream_keys),   # ← the important part
    }, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()
```

`upstream_keys` contains the cache keys of the stages this one consumed. That single field gives correct cascading invalidation for free: editing the question prompt changes stage 5's key, which changes stage 6's key, while stages 1–4 stay warm and cost nothing.

Rules:
- Never delete old runs. Mark superseded ones `stale`. You will want to compare question quality across prompt versions.
- Re-upload of an identical PDF (same sha256) is a no-op that reuses every stage.
- `POST /pipeline/{doc_id}/run?stages=questions,answers&force=true` re-runs a subset deliberately.

---

## 7. The analysis pipeline

Seven stages. Each writes exactly one `analysis_runs` row and is independently cacheable.

### 7.1 Stage 1 — ingest (no LLM)

- Extract text with **PyMuPDF**, preserving page numbers.
- Detect headings from font size/weight to build `section_path`. Fall back to regex on numbered headings (`^\d+(\.\d+)*\s+`) — Norwegian theses are near-universally numbered.
- Detect and separately tag figure captions (`^(Figur|Figure|Tabell|Table)\s*\d+`) as `kind='figure_caption'`. These are disproportionately question-generating and must survive chunking intact.
- Chunk at ~800 tokens with 120-token overlap, never crossing a top-level section boundary.
- Drop the reference list from question-generation chunks but keep it as `kind='reference'` for the literature stage.
- Embed with `multilingual-e5-large` locally (handles Norwegian well; no data leaves the machine, no per-token cost).

**Output:** `chunks` rows. Typical 80-page thesis → 120–200 chunks.

### 7.2 Stage 2 — structure map

Input: the full thesis text if it fits the context window (an 80-page thesis is roughly 40–60k tokens, so it usually does), otherwise abstract + intro + methods + results headers + all figure captions.

Output JSON:

```json
{
  "tittel": "...",
  "fagfelt": "...",
  "problemstilling": "...",
  "delmaal": ["...", "..."],
  "hypoteser": ["..."],
  "bidrag": ["..."],
  "metoder": [
    {"navn": "HPLC-MS/MS", "formaal": "...", "kapittel": "3.2", "side": 24,
     "alternativer_ikke_valgt": ["LC-UV", "GC-MS"]}
  ],
  "materialer": {"cellelinjer": [], "dyremodell": null, "humant_materiale": "...",
                 "reagenser_kritiske": ["..."]},
  "design": {"n": "...", "grupper": ["..."], "replikater": "...",
             "randomisering": "...", "blinding": "..."},
  "statistikk": {"tester": ["..."], "programvare": "...", "korreksjon": "..."},
  "hovedresultater": [
    {"funn": "...", "figur": "Figur 4.3", "side": 41, "effektstoerrelse": "...", "p": "..."}
  ],
  "oppgitte_begrensninger": ["..."],
  "etikk": {"rek": "...", "personvern": "...", "dyrevelferd": null},
  "kapitler": [{"nr": "4", "tittel": "Resultater", "side_start": 35, "side_slutt": 52}],
  "glossary": ["assay", "kalibreringskurve", "..."],
  "usikkert": ["Fields the model could not determine from the text"]
}
```

The `usikkert` array is a required output field. It surfaces where the analysis is guessing, which is exactly where a human review pass pays off. The UI shows it as a review banner on first load.

### 7.3 Stage 3 — claim extraction

For each results/discussion chunk, extract defensible claims with evidence references and a strength rating 1–5, where 5 = directly and robustly supported by the presented data, 1 = speculative extrapolation in the discussion. Target 25–60 claims.

The strength score matters: **low-strength claims in the discussion section are the single richest source of hard defence questions.** A thesis discussion typically over-reaches somewhere, and the external examiner will find it.

### 7.4 Stage 4 — vulnerability analysis

The highest-value stage. Input: structure map + claims + the §2.1 checklist verbatim.

Prompt shape:

```
You are an experienced external examiner (ekstern sensor) in pharmacy and health
sciences at a Norwegian university. You are reviewing a master's thesis before an
oral defence. Your job is to find, honestly and specifically, where this work is
weakest — not to be cruel, but because the candidate must be prepared.

Work through the checklist below against the thesis material. For each item that
applies, produce a vulnerability entry. Skip items that genuinely do not apply;
do not manufacture concerns.

<checklist>
{{ §2.1 checklist }}
</checklist>

For each vulnerability output:
  checklist_key   — the checklist item
  description     — the specific weakness in THIS thesis, referencing what the
                    candidate actually did (never generic)
  severity        — 1–5, how much a sharp examiner could damage the work with it
  attack_angle    — the question as an examiner would actually phrase it, in
                    Norwegian bokmål
  best_defence    — the honest strongest response available to the candidate,
                    in Norwegian. If the honest answer is a concession, say so.

Rules:
- Reference specific pages, figures, methods and numbers from the thesis.
- Never write a vulnerability that would apply to any thesis in this field.
- If the thesis handled a checklist item well, do not invent a problem with it.
```

Target 15–35 vulnerabilities.

### 7.5 Stage 5 — question generation

Input: structure map, claims, vulnerabilities.

Constraints in the prompt:
- Produce **120–180** questions.
- Fill the category × difficulty grid; specify a minimum count per cell (e.g. ≥4 per category, ≥25 at difficulty 4 overall).
- Every question carries `source_refs` with real page numbers. Questions that cannot be tied to a page get dropped in post-processing.
- Every question carries `why_asked` — one sentence explaining what the examiner is testing. Shown only after the answer.
- Every question carries 1–3 `follow_ups` — the escalation an examiner would use if the first answer was thin.
- Questions are **spoken**, so: one question per question. No compound multi-part questions. Under 40 words. Natural spoken Norwegian, not written academic register.
- `expected_shape` set per question.
- Category `kritisk` questions must challenge a premise, not just ask harder.

Post-processing in code: near-duplicate removal via embedding cosine similarity > 0.92, drop questions with empty `source_refs`, enforce per-cell minimums by re-prompting for underfilled cells only.

### 7.6 Stage 6 — model answers and rubrics

Per question, generate:
- `model_answer` — Norwegian, 100–140 words, i.e. speakable in about 60 seconds. Must demonstrate the `expected_shape`. Where the honest answer is a concession, the model answer must concede.
- `rubric` — four dimensions with 0–4 anchors specific to *this* question, plus `noekkelpunkter` (the 3–5 points a good answer contains) and `roede_flagg` (claims that would be wrong or over-reaching).

Batch 10 questions per call. This stage is the token-heavy one; it is also the one you will re-run least.

### 7.7 Stage 7 — study summaries

For Study mode. Generate, in Norwegian:
- **Ryggraden** (the spine) — one page: problemstilling, bidrag i 3 setninger, metode i 3 setninger, tre hovedfunn, største begrensning. This is the single most useful artefact in the whole system.
- One summary per chapter — what it does, why it exists, what it establishes for the next chapter.
- One summary per key concept/method (from `metoder`) — principle, why chosen, assumptions, failure modes, the level beneath it.
- One summary per major figure/table — what it shows, effect size, uncertainty, what would have falsified it.

---

## 8. Voice loop

### 8.1 Flow

```
question selected
  → TTS (cached) → presigned URL → autoplay
  → recorder arms on audio end
  → MediaRecorder captures webm/opus, 250 ms timeslice
  → VAD watches RMS; 2.5 s below threshold → auto-stop
  → hard stop at ANSWER_TIME_LIMIT_S + 30 s grace
  → upload blob → MinIO
  → POST /turns/{id}/answer → enqueue transcription
  → STT → transcript + confidence
  → delivery metrics computed in code
  → drill: grade now, stream via SSE
    exam: mark 'transcribed', defer
  → next question
```

### 8.2 Recording

- `MediaRecorder` with `audio/webm;codecs=opus`, 48 kHz mono, ~32 kbps. A 90-second answer is ~360 KB.
- `getUserMedia` constraints: `echoCancellation: false`, `noiseSuppression: false`, `autoGainControl: false`. Browser speech processing distorts pace and pause structure, which are things being measured. Leave the signal alone.
- Request mic permission once on session start, not per question.

### 8.3 Voice activity detection

Web Audio `AnalyserNode`, RMS over 20 ms frames, adaptive noise floor calibrated from the first 500 ms of room tone. Speech threshold = noise floor × 4, floored at a small absolute value. Stop after `VAD_SILENCE_MS` continuous silence.

Never auto-stop in the first 3 seconds — thinking pauses before starting are normal and cutting them off is infuriating. Manual stop button always visible and always wins.

### 8.4 The visible timer

A 90-second ring that fills as you speak. Green → amber at 75 s → red at 90 s. It does not cut you off; it trains the instinct.

This is a training feature, not a constraint. Over-answering is the most common failure mode in real defences because it hands the examiner new surface to attack. Seeing the ring go red is how you learn to stop.

### 8.5 STT service contract

```
POST /transcribe
  multipart: file=<audio>, language=no, initial_prompt=<glossary terms>
  → 200 { "text": "...", "segments": [...], "avg_logprob": -0.31, "duration_s": 78.4 }
```

Wraps faster-whisper with a warm model held in memory. Single worker, single concurrency — you are one person and queueing is fine.

### 8.6 Latency budget

| Segment | Target | Notes |
|---|---|---|
| Question TTS | 0 ms | Pre-cached; also prefetch next question's audio during current answer |
| Upload | <500 ms | Local network |
| STT | <3 s | GPU. On CPU this blows the budget — see §5.4 |
| Grading | 4–8 s | Streamed, so first feedback token appears in ~1.5 s |
| **Drill turn gap** | ~5–10 s | Acceptable; feedback is being read anyway |
| **Exam turn gap** | **<2 s** | Grading deferred, so only upload matters |

Exam mode must feel continuous. If the gap between answering and the next question exceeds about 2 seconds, the simulation stops feeling like a defence.

### 8.7 Deferred grading in exam mode

During an exam session, turns are recorded, uploaded and queued only. No score, no feedback, no indication of quality. On session end the worker transcribes and grades everything, and the report appears when ready.

This is a deliberate design constraint, not a performance shortcut. The skill of recovering from a weak answer and staying composed for the next question only trains when feedback is withheld. A tool that scores you after every answer teaches a habit that actively hurts on the day.

### 8.8 Grading

**Split the judgement.** Content goes to the LLM. Delivery is computed in code:

```python
FILLERS_NO = {"eh","øh","ehm","liksom","altså","på en måte","ikke sant",
              "sånn","da","jo","vel","egentlig"}
```

Compute: `wpm`, `filler_count`, `filler_rate`, `longest_pause_ms` (from Whisper segment gaps), `time_to_first_word_ms`, `duration_ms`.

Norwegian reference band: 130–160 wpm is a composed, audible pace. Above ~180 reads as nervous rushing. Below ~110 reads as hesitant.

Careful with the filler list: *altså*, *da*, *jo* and *vel* are legitimate discourse particles in Norwegian and not always fillers. Count them, but weight them at half and never surface them as errors — surface only `eh/øh/ehm` as hard fillers and report the rest as a "muntlig fyll" tendency.

**Grading prompt essentials:**

```
You are grading a SPOKEN answer given under exam pressure, transcribed
automatically. Grade substance only.

Do NOT penalise: self-correction, restarts, filler words, informal syntax,
incomplete sentences, or anything that is a normal feature of speech.
Do NOT penalise minor transcription artefacts.

Do reward: a clean, well-reasoned admission of not knowing something.
Do penalise: confident assertions that are not supported by the thesis (bluffing).

Score 0–4 on each:
  korrekthet   — factually right about the candidate's own work
  begrunnelse  — explains WHY, not only WHAT
  forbehold    — acknowledges limits, conditions, uncertainty
  struktur     — has a clear shape; concise; answers the question asked

Also return:
  bluffed        — boolean
  used_shape     — direkte | utfordre | innrommelse | uklar
  missed_points  — key points from the rubric that were not covered
  feedback_md    — 3–5 sentences in Norwegian bokmål, direct and specific.
                   Lead with the single most useful correction. No praise padding.
```

Feed the grader: question, `why_asked`, rubric, model answer, transcript, and the relevant source chunks so it can check factual claims against the actual thesis.

---

## 9. Application surfaces

### 9.1 Routes

| Route | Norwegian nav label | Purpose |
|---|---|---|
| `/opplasting` | Last opp | Upload PDF, watch pipeline progress |
| `/bibliotek/[docId]` | Bibliotek | Study mode: spine, chapters, concepts, claims, vulnerabilities |
| `/trening/[sessionId]` | Trening | Drill mode |
| `/eksamen/[sessionId]` | Eksamen | Mock defence |
| `/oversikt` | Oversikt | Dashboard, history, plan |

### 9.2 Study mode (`/bibliotek`)

Left rail: Ryggraden · Kapitler · Begreper og metoder · Figurer · Påstander · Svakheter.

The **Svakheter** view is the one to get right: vulnerabilities sorted by severity, each showing the attack angle as an examiner would phrase it and the honest best defence, with a "Øv på denne" button that starts a drill session filtered to questions from that vulnerability.

Every card carries its page reference and links back to the PDF page. Jumping from a question to page 47 of your own thesis is what makes this a tool rather than a novelty.

### 9.3 Drill mode (`/trening`)

Chat-like column. Examiner turn: avatar, question text, audio autoplay, replay button. Candidate turn: waveform, timer ring, transcript appearing after STT, then the feedback panel.

Feedback panel: four-dimension score bars, `feedback_md`, missed points, delivery strip (duration, wpm, fillers), collapsible model answer, `why_asked`, source page links, and a "Still oppfølgingsspørsmål" button that asks the escalation question.

Session config: categories, difficulty range, question count, examiner persona.

**Examiner personas** (affects TTS voice and question phrasing, not content):

| Persona | Norwegian | Behaviour |
|---|---|---|
| `vennlig` | Vennlig sensor | Neutral phrasing, no escalation |
| `grundig` | Grundig sensor | Always asks one follow-up |
| `krevende` | Krevende ekstern sensor | Premise-challenging, escalates on weak answers |

Run `krevende` from day 10 onwards.

### 9.4 Exam mode (`/eksamen`)

Full-screen, minimal chrome. 45-minute default. Question counter, elapsed time, current question text (small — it is meant to be heard), recording indicator. **No scores anywhere.**

Question selection: weighted draw, no repeats within session. Weighting favours categories with low historical mean score and questions never attempted, with a floor so every category can appear. Difficulty distribution roughly 20/30/30/20 across tiers 1–4.

On end: `Sesjonen er avsluttet. Rapporten er klar om et par minutter.` Report shows per-question scores, weakest answers first, delivery trend, category breakdown, and playback of every answer.

### 9.5 Dashboard (`/oversikt`)

- **Dekningskart** — chapter × category heatmap, coloured by mean score, grey where unattempted. The grey cells are the point.
- **Svakeste ti** — worst-scoring questions, one click to drill them.
- **Utvikling** — mean score and mean answer duration over time. Duration trending down while score holds steady is the signal you are actually improving.
- **Leveringsstatistikk** — wpm and filler rate per session.
- **Plan** — 14-day checklist from `plan_items`, seeded on first document ingest, each day linking to a filtered drill session.

### 9.6 Presentation support (minimal)

One feature only: a 20-minute timer with section marks for practising the talk, storing duration per run so you can see it converging. No slide analysis, no scoring.

### 9.7 Design direction

The subject's own world supplies the visual language: this is laboratory work and a formal Norwegian academic occasion. Avoid the default "AI dashboard" look — dark navy with a violet gradient and rounded cards everywhere.

Suggested direction: an instrument-panel aesthetic. Near-white paper background (#FAFAF7), ink near-black text, a single saturated accent used only for the recording state, and a muted amber/red reserved exclusively for the timer. Type: a characterful serif for question text — questions are the content, they should read as authored and weighty — against a neutral grotesk for UI chrome and a monospace for numbers, timings and page references. Set questions large. Everything else quiet.

The signature element: the timer ring around the record button, which is the one place the interface should feel alive.

Norwegian copy rules: sentence case throughout, active verbs on buttons (`Start trening`, `Ta opp svar`, `Avslutt sesjonen`), and empty states that direct rather than apologise (`Ingen sesjoner ennå. Start med en kort treningsrunde på ti spørsmål.`).

---

## 10. API surface

```
GET    /health

POST   /documents                       multipart pdf → {id, sha256, existing: bool}
GET    /documents/{id}
GET    /documents/{id}/pdf              → presigned URL
DELETE /documents/{id}

POST   /pipeline/{doc_id}/run           ?stages=...&force=bool → {run_ids}
GET    /pipeline/{doc_id}/status        → per-stage status, cost, cached?
GET    /pipeline/runs/{run_id}

GET    /documents/{id}/map
GET    /documents/{id}/summaries        ?scope=
GET    /documents/{id}/claims
GET    /documents/{id}/vulnerabilities
GET    /documents/{id}/questions        ?category=&difficulty=&limit=&unattempted=
PATCH  /questions/{id}                  {retired, text}   ← manual quality control
GET    /questions/{id}/audio            → presigned URL, generates+caches on miss

POST   /sessions                        {document_id, mode, config} → session + first turn
GET    /sessions/{id}
GET    /sessions/{id}/next              → next turn with question + audio URL
POST   /sessions/{id}/end               → triggers deferred grading in exam mode
GET    /sessions/{id}/report

POST   /turns/{id}/answer               multipart audio → {status}
GET    /turns/{id}
GET    /turns/{id}/grade/stream         SSE, drill mode only
POST   /turns/{id}/follow-up            → new turn from question.follow_ups
POST   /turns/{id}/skip

GET    /stats/coverage                  ?document_id=
GET    /stats/weakest                   ?document_id=&limit=10
GET    /stats/progress                  ?document_id=

GET    /plan                            ?document_id=
PATCH  /plan/{item_id}                  {done}
```

SSE is used only for grade streaming. Everything else is plain REST with polling on the pipeline status endpoint — a 2-second poll for a job that runs once per document is not worth a websocket.

---

## 11. Build order

Ordered by risk, not by layer. The voice loop is the highest-risk component and comes before anything that depends on it being pretty.

| # | Milestone | Done when |
|---|---|---|
| 1 | Compose skeleton | `docker compose up` → all healthy, `/health` returns 200, Alembic migration applied |
| 2 | Upload + ingest | PDF uploads, chunks and embeddings in Postgres, page numbers correct on spot-check |
| 3 | Stage 2 structure map | JSON map correct on manual review; `usikkert` reviewed |
| 4 | **Voice loop, one hardcoded question** | TTS plays, mic records, STT returns Norwegian transcript, round trip under 10 s |
| 5 | Stages 3–6 | 120+ questions with page refs, model answers, rubrics |
| 6 | Drill mode | Full loop with real grading and feedback |
| 7 | Stage 7 + Study mode | Spine and chapter summaries readable |
| 8 | Exam mode + deferred grading | 45-min session runs end to end, report generates |
| 9 | Dashboard + plan | Coverage map, weakest ten, 14-day checklist |

**Abort condition:** if milestone 4 is not working by end of day 2, stop building the voice loop. Fall back to typed answers in the app and drill vocally offline with a phone recorder. The preparation is the deliverable; the app is instrumental. Do not let the tool eat the two weeks.

---

## 12. Operational concerns

### 12.1 Cost

Rough per-thesis estimate at current mid-tier LLM pricing, 80-page thesis:

| Stage | Input | Output | Est. |
|---|---|---|---|
| 2 structure | ~55k | ~3k | $0.20 |
| 3 claims | ~60k | ~8k | $0.30 |
| 4 vulnerabilities | ~20k | ~10k | $0.20 |
| 5 questions | ~25k | ~25k | $0.45 |
| 6 answers/rubrics | ~180k batched | ~60k | $1.50 |
| 7 summaries | ~60k | ~15k | $0.35 |
| **Full pipeline** | | | **~$3** |
| Grading per turn | ~4k | ~600 | ~$0.02 |

600 practice answers over two weeks ≈ $12. Total well under $30. The caching design exists to keep prompt iteration cheap, not to control total spend.

Log `input_tokens`, `output_tokens` and `cost_usd` on every run and display cumulative cost on the pipeline status page.

### 12.2 Reliability

- LLM calls: 3 retries, exponential backoff, jitter. On JSON parse failure, one repair attempt that feeds the malformed output back with the schema.
- All stage outputs validated against Pydantic models before persisting. A stage that produces invalid JSON fails loudly rather than writing garbage.
- Worker jobs idempotent on cache key.
- STT failure on a turn → mark `status='recorded'`, keep the audio, allow manual retry. Never lose a recording.

### 12.3 Quality control on generated questions

Automated generation produces some duds. Budget 30 minutes on day 1 to skim the question list and hit `PATCH /questions/{id}` with `retired: true` on anything hallucinated or trivial. Retired questions never appear in draws. This step matters more than any prompt tuning.

### 12.4 Backups

`pg_dump` to a mounted host directory nightly via a cron container, plus a `make backup` target. Two weeks of recorded answers and scores is data you would be annoyed to lose on a `docker compose down -v`.

---

## 13. Norwegian UI string reference

Centralise in `web/lib/nb.ts`. Selected entries:

```ts
export const nb = {
  nav: { last_opp: "Last opp", bibliotek: "Bibliotek", trening: "Trening",
         eksamen: "Eksamen", oversikt: "Oversikt" },
  upload: {
    title: "Last opp masteroppgaven",
    drop: "Dra PDF-en hit, eller velg fil",
    analysing: "Analyserer oppgaven. Dette tar noen minutter og gjøres bare én gang.",
    cached: "Denne oppgaven er analysert fra før. Innholdet hentes fra databasen.",
  },
  drill: {
    start: "Start trening",
    record: "Ta opp svar",
    stop: "Stopp opptak",
    listening: "Hører etter …",
    transcribing: "Skriver ut svaret …",
    grading: "Vurderer svaret …",
    model_answer: "Vis eksempelsvar",
    why: "Hvorfor spørsmålet stilles",
    follow_up: "Still oppfølgingsspørsmål",
    next: "Neste spørsmål",
  },
  exam: {
    start: "Start eksamenssimulering",
    running: "Sesjonen pågår. Du får tilbakemelding når den er ferdig.",
    end: "Avslutt sesjonen",
    ended: "Sesjonen er avsluttet. Rapporten er klar om et par minutter.",
  },
  scores: {
    korrekthet: "Korrekthet",
    begrunnelse: "Begrunnelse",
    forbehold: "Forbehold og begrensninger",
    struktur: "Struktur og presisjon",
  },
  delivery: {
    duration: "Varighet", wpm: "Ord per minutt",
    fillers: "Fyllord", pause: "Lengste pause",
  },
  empty: {
    sessions: "Ingen sesjoner ennå. Start med en kort treningsrunde på ti spørsmål.",
    weakest: "Ikke nok data ennå. Svar på minst ti spørsmål.",
  },
  errors: {
    mic: "Fikk ikke tilgang til mikrofonen. Sjekk nettleserinnstillingene.",
    stt: "Klarte ikke å skrive ut svaret. Opptaket er lagret — prøv på nytt.",
    upload: "Opplastingen feilet. Filen må være en PDF under 50 MB.",
  },
};
```

---

## 14. Risks

| Risk | Mitigation |
|---|---|
| Building displaces preparing | Milestone 4 abort condition (§11). Hard cap: 3 days of build. |
| STT too slow on CPU | Use `nb-whisper-small` for drill; exam mode defers anyway |
| Generated questions too generic | Vulnerability stage grounds questions in specifics; manual retirement pass (§12.3) |
| Grader penalises normal speech | Explicit instruction in grading prompt; delivery scored separately in code |
| Practising against a model, not people | Non-negotiable: at least two mock defences with a human. The app supplements, never replaces. |
| Over-fitting to generated questions | Rotate categories; never drill the same 30 questions repeatedly |

---

## 15. Open questions

1. **Hours per day** available, and any unavailable days in the two weeks — determines whether the plan compresses.
2. **GPU available?** Decides STT model size and whether drill mode feels fast.
3. **Thesis page count** and figure/table count.
4. **Is the thesis written in Norwegian or English?** Affects nothing structurally, but changes the terminology instruction in the prompts and whether the glossary needs bilingual entries.
5. **Institution and whether the defence is grade-adjusting** (*justerende muntlig*) — changes how hard to push on tier-4 questions.
6. **Local TTS or cloud voice?** Cloud costs a little and sounds materially better; local is free and offline.
