from arq import cron
from arq.connections import RedisSettings

from app.config import settings
from app.worker import stages  # noqa: F401


class WorkerSettings:
    functions = [
        stages.run_pipeline_stage,
        stages.grade_turn,
        stages.grade_session,
    ]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    max_jobs = 2
    job_timeout = 600
