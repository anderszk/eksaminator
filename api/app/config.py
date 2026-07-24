from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://app:app@postgres:5432/defence"
    redis_url: str = "redis://redis:6379/0"

    s3_endpoint: str = "http://minio:9000"
    s3_bucket: str = "defence"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"

    stt_url: str = "http://stt:9001"
    tts_url: str = "http://tts:9002"

    anthropic_api_key: str = ""
    llm_model: str = "claude-sonnet-4-6"
    llm_max_tokens: int = 8000

    embedding_model: str = "intfloat/multilingual-e5-large"
    embedding_dim: int = 1024

    answer_time_limit_s: int = 90
    vad_silence_ms: int = 2500
    prompt_version: str = "v1"

    tts_provider: str = "piper"
    piper_voice: str = "nb_NO-talesyntese-medium"
    azure_speech_key: str = ""
    azure_speech_region: str = "norwayeast"
    azure_tts_voice: str = "nb-NO-PernilleNeural"


settings = Settings()
