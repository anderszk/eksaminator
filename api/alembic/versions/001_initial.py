"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-07-24
"""
from alembic import op

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    op.execute("""
        CREATE TYPE pipeline_stage AS ENUM (
          'ingest','structure','claims','vulnerabilities','questions','answers','summaries'
        )
    """)
    op.execute("CREATE TYPE run_status AS ENUM ('pending','running','done','failed','stale')")
    op.execute("CREATE TYPE session_mode AS ENUM ('drill','exam')")
    op.execute("CREATE TYPE turn_status AS ENUM ('pending','recorded','transcribed','graded','skipped')")

    op.execute("""
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
        )
    """)

    op.execute("""
        CREATE TABLE chunks (
          id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          document_id   uuid NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
          ordinal       int  NOT NULL,
          page_start    int  NOT NULL,
          page_end      int  NOT NULL,
          section_path  text,
          kind          text NOT NULL DEFAULT 'text',
          text          text NOT NULL,
          token_count   int  NOT NULL,
          embedding     vector(1024),
          UNIQUE (document_id, ordinal)
        )
    """)
    op.execute("CREATE INDEX chunks_doc_idx ON chunks (document_id, ordinal)")
    op.execute("CREATE INDEX chunks_vec_idx ON chunks USING hnsw (embedding vector_cosine_ops)")
    op.execute("CREATE INDEX chunks_fts_idx ON chunks USING gin (to_tsvector('norwegian', text))")

    op.execute("""
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
        )
    """)
    op.execute("""
        CREATE UNIQUE INDEX analysis_runs_cache_idx
          ON analysis_runs (cache_key) WHERE status = 'done'
    """)
    op.execute("""
        CREATE INDEX analysis_runs_doc_stage_idx
          ON analysis_runs (document_id, stage, created_at DESC)
    """)

    op.execute("""
        CREATE TABLE thesis_map (
          run_id        uuid PRIMARY KEY REFERENCES analysis_runs(id) ON DELETE CASCADE,
          document_id   uuid NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
          data          jsonb NOT NULL
        )
    """)

    op.execute("""
        CREATE TABLE claims (
          id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          run_id        uuid NOT NULL REFERENCES analysis_runs(id) ON DELETE CASCADE,
          document_id   uuid NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
          text          text NOT NULL,
          claim_type    text NOT NULL,
          evidence_refs jsonb NOT NULL,
          strength      int  NOT NULL CHECK (strength BETWEEN 1 AND 5),
          created_at    timestamptz NOT NULL DEFAULT now()
        )
    """)

    op.execute("""
        CREATE TABLE vulnerabilities (
          id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          run_id        uuid NOT NULL REFERENCES analysis_runs(id) ON DELETE CASCADE,
          claim_id      uuid REFERENCES claims(id) ON DELETE CASCADE,
          document_id   uuid NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
          checklist_key text NOT NULL,
          description   text NOT NULL,
          severity      int  NOT NULL CHECK (severity BETWEEN 1 AND 5),
          attack_angle  text NOT NULL,
          best_defence  text
        )
    """)

    op.execute("""
        CREATE TABLE questions (
          id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          run_id           uuid NOT NULL REFERENCES analysis_runs(id) ON DELETE CASCADE,
          document_id      uuid NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
          claim_id         uuid REFERENCES claims(id) ON DELETE SET NULL,
          vulnerability_id uuid REFERENCES vulnerabilities(id) ON DELETE SET NULL,
          category         text NOT NULL,
          difficulty       int  NOT NULL CHECK (difficulty BETWEEN 1 AND 4),
          text             text NOT NULL,
          why_asked        text NOT NULL,
          expected_shape   text NOT NULL,
          source_refs      jsonb NOT NULL,
          follow_ups       jsonb DEFAULT '[]',
          model_answer     text,
          rubric           jsonb,
          tts_key          text,
          retired          boolean NOT NULL DEFAULT false,
          created_at       timestamptz NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX questions_doc_idx ON questions (document_id, category, difficulty)")

    op.execute("""
        CREATE TABLE summaries (
          id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          run_id       uuid NOT NULL REFERENCES analysis_runs(id) ON DELETE CASCADE,
          document_id  uuid NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
          scope        text NOT NULL,
          ref          text NOT NULL,
          title        text NOT NULL,
          body_md      text NOT NULL,
          source_refs  jsonb NOT NULL,
          ordinal      int NOT NULL DEFAULT 0
        )
    """)

    op.execute("""
        CREATE TABLE sessions (
          id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          document_id  uuid NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
          mode         session_mode NOT NULL,
          config       jsonb NOT NULL DEFAULT '{}',
          started_at   timestamptz NOT NULL DEFAULT now(),
          ended_at     timestamptz,
          summary      jsonb
        )
    """)

    op.execute("""
        CREATE TABLE turns (
          id                    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          session_id            uuid NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
          question_id           uuid NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
          ordinal               int  NOT NULL,
          status                turn_status NOT NULL DEFAULT 'pending',
          is_follow_up          boolean NOT NULL DEFAULT false,
          parent_turn_id        uuid REFERENCES turns(id) ON DELETE SET NULL,
          answer_s3_key         text,
          transcript            text,
          stt_confidence        real,
          duration_ms           int,
          wpm                   real,
          filler_count          int,
          filler_rate           real,
          longest_pause_ms      int,
          time_to_first_word_ms int,
          scores                jsonb,
          bluffed               boolean,
          used_shape            text,
          feedback_md           text,
          missed_points         jsonb,
          asked_at              timestamptz,
          answered_at           timestamptz,
          graded_at             timestamptz,
          UNIQUE (session_id, ordinal)
        )
    """)
    op.execute("CREATE INDEX turns_question_idx ON turns (question_id, graded_at DESC)")

    op.execute("""
        CREATE TABLE plan_items (
          id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          document_id  uuid REFERENCES documents(id) ON DELETE CASCADE,
          day          int  NOT NULL CHECK (day BETWEEN 1 AND 14),
          title        text NOT NULL,
          detail_md    text,
          minutes      int,
          kind         text NOT NULL,
          done         boolean NOT NULL DEFAULT false,
          linked_categories text[] DEFAULT '{}',
          ordinal      int NOT NULL DEFAULT 0
        )
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS plan_items")
    op.execute("DROP TABLE IF EXISTS turns")
    op.execute("DROP TABLE IF EXISTS sessions")
    op.execute("DROP TABLE IF EXISTS summaries")
    op.execute("DROP TABLE IF EXISTS questions")
    op.execute("DROP TABLE IF EXISTS vulnerabilities")
    op.execute("DROP TABLE IF EXISTS claims")
    op.execute("DROP TABLE IF EXISTS thesis_map")
    op.execute("DROP TABLE IF EXISTS analysis_runs")
    op.execute("DROP TABLE IF EXISTS chunks")
    op.execute("DROP TABLE IF EXISTS documents")
    op.execute("DROP TYPE IF EXISTS turn_status")
    op.execute("DROP TYPE IF EXISTS session_mode")
    op.execute("DROP TYPE IF EXISTS run_status")
    op.execute("DROP TYPE IF EXISTS pipeline_stage")
