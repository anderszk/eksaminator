import uuid

from fastapi import APIRouter, UploadFile

from app.schemas.schemas import DocumentOut, DocumentUploadOut

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("", response_model=DocumentUploadOut)
async def upload_document(file: UploadFile):
    raise NotImplementedError


@router.get("/{doc_id}", response_model=DocumentOut)
async def get_document(doc_id: uuid.UUID):
    raise NotImplementedError


@router.get("/{doc_id}/pdf")
async def get_document_pdf_url(doc_id: uuid.UUID):
    raise NotImplementedError


@router.delete("/{doc_id}", status_code=204)
async def delete_document(doc_id: uuid.UUID):
    raise NotImplementedError
