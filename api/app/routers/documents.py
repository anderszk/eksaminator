import asyncio
import hashlib
import uuid

import boto3
from botocore.exceptions import ClientError
from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_db
from app.models.models import Document
from app.schemas.schemas import DocumentOut, DocumentRenameIn, DocumentUploadOut

router = APIRouter(prefix="/documents", tags=["documents"])

MAX_SIZE = 50 * 1024 * 1024  # 50 MB


@router.get("", response_model=list[DocumentOut])
async def list_documents(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).order_by(Document.uploaded_at.desc()))
    return result.scalars().all()


def _s3():
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name="us-east-1",
    )


@router.post("", response_model=DocumentUploadOut)
async def upload_document(file: UploadFile, db: AsyncSession = Depends(get_db)):
    if file.content_type != "application/pdf":
        raise HTTPException(400, "Filen må være en PDF.")

    pdf_bytes = await file.read()
    if len(pdf_bytes) > MAX_SIZE:
        raise HTTPException(400, "Filen er for stor (maks 50 MB).")

    sha = hashlib.sha256(pdf_bytes).hexdigest()

    # Check if already exists
    result = await db.execute(select(Document).where(Document.sha256 == sha))
    existing = result.scalar_one_or_none()
    if existing:
        return DocumentUploadOut(id=existing.id, sha256=sha, existing=True)

    # Upload to MinIO
    s3_key = f"pdfs/{sha}.pdf"
    await asyncio.to_thread(
        lambda: _s3().put_object(
            Bucket=settings.s3_bucket,
            Key=s3_key,
            Body=pdf_bytes,
            ContentType="application/pdf",
        )
    )

    doc = Document(
        filename=file.filename or "oppgave.pdf",
        sha256=sha,
        page_count=0,  # updated after ingest
        char_count=0,
        s3_key=s3_key,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    return DocumentUploadOut(id=doc.id, sha256=sha, existing=False)


@router.get("/{doc_id}", response_model=DocumentOut)
async def get_document(doc_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Dokument ikke funnet.")
    return doc


@router.get("/{doc_id}/pdf")
async def get_document_pdf_url(doc_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Dokument ikke funnet.")

    url = await asyncio.to_thread(
        lambda: _s3().generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.s3_bucket, "Key": doc.s3_key},
            ExpiresIn=3600,
        )
    )
    return {"url": url}


@router.patch("/{doc_id}", response_model=DocumentOut)
async def rename_document(doc_id: uuid.UUID, body: DocumentRenameIn, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Dokument ikke funnet.")

    title = body.title.strip()
    if not title:
        raise HTTPException(400, "Tittel kan ikke være tom.")

    doc.title = title
    await db.commit()
    await db.refresh(doc)
    return doc


@router.delete("/{doc_id}", status_code=204)
async def delete_document(doc_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Dokument ikke funnet.")

    await asyncio.to_thread(
        lambda: _s3().delete_object(Bucket=settings.s3_bucket, Key=doc.s3_key)
    )
    await db.delete(doc)
    await db.commit()
