from fastapi import APIRouter

router = APIRouter(prefix="/media", tags=["media"])
# Presigned URL generation for MinIO blobs (audio playback, PDF viewing).
# Routes added here as needed.
