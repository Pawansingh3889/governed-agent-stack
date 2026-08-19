"""Document upload and search API endpoints."""
from __future__ import annotations

import os
import tempfile

from fastapi import APIRouter, Depends, File, Form, UploadFile

from api.auth import get_current_user
from api.schemas import DocumentCount, DocumentSearchResult, DocumentUploadResponse
from modules.doc_search import get_doc_count, ingest_pdf
from modules.doc_search import search as doc_search

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
) -> DocumentUploadResponse:
    """Upload and ingest a PDF document into the vector store."""
    suffix = os.path.splitext(file.filename or "upload.pdf")[1] or ".pdf"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        if suffix.lower() == ".pdf":
            chunks = ingest_pdf(tmp_path)
        else:
            chunks = ingest_pdf(tmp_path)  # falls back to text for non-PDFs
    finally:
        os.unlink(tmp_path)

    return DocumentUploadResponse(filename=file.filename or "upload", chunk_count=chunks)


@router.post("/search", response_model=list[DocumentSearchResult])
async def search_documents(
    query: str = Form(...),
    top_k: int = Form(5),
    user: dict = Depends(get_current_user),
) -> list[DocumentSearchResult]:
    """Search the document vector store."""
    results = doc_search(query, n_results=top_k)
    return [
        DocumentSearchResult(
            text=r.get("text", ""),
            score=round(1 - r.get("distance", 0), 3),
            source=r.get("metadata", {}).get("source", "Unknown"),
            category=r.get("metadata", {}).get("category", "general"),
            page=r.get("metadata", {}).get("page"),
        )
        for r in results
    ]


@router.get("/count", response_model=DocumentCount)
async def document_count(user: dict = Depends(get_current_user)) -> DocumentCount:
    """Return the total number of document chunks indexed."""
    return DocumentCount(count=get_doc_count())
