from arq.connections import RedisSettings

from app.config import settings
from app.worker.stages import grade_session, grade_turn, run_pipeline_stage


class WorkerSettings:
    functions = [run_pipeline_stage, grade_turn, grade_session]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    max_jobs = 2
    job_timeout = 600
    keep_result = 3600
