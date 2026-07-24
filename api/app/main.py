import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config import settings
from app.db import SessionLocal
from app.routers import content, documents, media, pipeline, sessions, turns

logger = logging.getLogger(__name__)


async def _ensure_minio_bucket() -> None:
    import asyncio
    import boto3
    from botocore.exceptions import ClientError

    def _create():
        client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            region_name="us-east-1",
        )
        try:
            client.head_bucket(Bucket=settings.s3_bucket)
        except ClientError:
            client.create_bucket(Bucket=settings.s3_bucket)
            logger.info("Created MinIO bucket: %s", settings.s3_bucket)

    await asyncio.to_thread(_create)


@asynccontextmanager
async def lifespan(app: FastAPI):
    for attempt in range(10):
        try:
            await _ensure_minio_bucket()
            break
        except Exception as exc:
            if attempt == 9:
                logger.error("MinIO not ready after 10 attempts: %s", exc)
            else:
                await asyncio.sleep(2)
    yield


app = FastAPI(title="Eksaminator API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(documents.router)
app.include_router(pipeline.router)
app.include_router(content.router)
app.include_router(sessions.router)
app.include_router(turns.router)
app.include_router(media.router)


@app.get("/health")
async def health():
    try:
        async with SessionLocal() as db:
            await db.execute(text("SELECT 1"))
        return {"status": "ok", "db": "ok"}
    except Exception as exc:
        return {"status": "degraded", "db": str(exc)}
