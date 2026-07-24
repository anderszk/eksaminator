"""TTS synthesis with MinIO caching. Every question is synthesized once per (id, voice, version)."""
import asyncio
import logging

import boto3
import httpx
from botocore.exceptions import ClientError

from app.config import settings

logger = logging.getLogger(__name__)


def get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name="us-east-1",
    )


def _key(question_id: str, voice: str, prompt_version: str) -> str:
    return f"tts/{question_id}_{voice}_{prompt_version}.wav"


def _exists(s3_key: str) -> bool:
    client = get_s3_client()
    try:
        client.head_object(Bucket=settings.s3_bucket, Key=s3_key)
        return True
    except ClientError:
        return False


def _upload(s3_key: str, data: bytes) -> None:
    client = get_s3_client()
    client.put_object(
        Bucket=settings.s3_bucket,
        Key=s3_key,
        Body=data,
        ContentType="audio/wav",
    )


async def synthesize_and_cache(
    question_id: str,
    text: str,
    voice: str,
    prompt_version: str,
) -> str:
    """Return MinIO key for the question audio, synthesizing if not cached."""
    s3_key = _key(question_id, voice, prompt_version)

    exists = await asyncio.to_thread(_exists, s3_key)
    if exists:
        logger.debug("TTS cache hit: %s", s3_key)
        return s3_key

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{settings.tts_url}/synthesize",
            json={"text": text, "voice": voice},
        )
        resp.raise_for_status()
        audio_bytes = resp.content

    await asyncio.to_thread(_upload, s3_key, audio_bytes)
    logger.info("TTS synthesized and cached: %s", s3_key)
    return s3_key


def get_presigned_url(s3_key: str, expires: int = 3600) -> str:
    client = get_s3_client()
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.s3_bucket, "Key": s3_key},
        ExpiresIn=expires,
    )
