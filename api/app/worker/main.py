from arq.connections import RedisSettings

from app.config import settings
from app.worker.stages import grade_session, grade_turn, on_startup, run_pipeline_stage


class WorkerSettings:
    functions = [run_pipeline_stage, grade_turn, grade_session]
    on_startup = on_startup
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    max_jobs = 2
    # answers/summaries stages make several sequential LLM calls (batches of 10
    # questions each, full model-answer + rubric per question) — for a document
    # with many questions this legitimately runs past 10 minutes. 600s was killing
    # otherwise-healthy runs mid-batch.
    job_timeout = 1800
    keep_result = 3600
