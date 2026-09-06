"""
POST /api/documents

Implements the document upload endpoint the frontend's composer already
expects (see app/src/services/api.ts -> uploadDocument, which posts
multipart/form-data with a single "file" field and expects back
{id, name, type, size, status}).
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Request, UploadFile

import base64

import config
from documents import store
from documents.parser import SUPPORTED_EXTENSIONS, SUPPORTED_IMAGE_EXTENSIONS, extract_text, sniff_image_mime
from documents.rag import process_and_store_document
from rate_limit import RateLimiter

router = APIRouter()

store.init_db()

upload_limiter = RateLimiter(config.RATE_LIMIT_UPLOADS_PER_MINUTE, window_seconds=60)


def _safe_suffix(filename: str) -> str:
    # Never trust the client filename for anything beyond its extension,
    # and never use it to build a filesystem path (path traversal
    # protection per item 32).
    return Path(filename).suffix.lower()


@router.post("/documents")
async def upload_document(request: Request, file: UploadFile = File(...)):
    if config.RATE_LIMIT_ENABLED:
        client_ip = request.client.host if request.client else "unknown"
        allowed, retry_after = upload_limiter.check(client_ip)
        if not allowed:
            raise HTTPException(
                status_code=429,
                detail=f"Too many uploads from this client. Try again in {retry_after:.0f}s.",
                headers={"Retry-After": str(int(retry_after) + 1)},
            )

    filename = Path(file.filename or "upload").name  # strip any directory components
    suffix = _safe_suffix(filename)

    is_image_ext = suffix in SUPPORTED_IMAGE_EXTENSIONS
    is_doc_ext = suffix in SUPPORTED_EXTENSIONS
    if not is_image_ext and not is_doc_ext:
        accepted = sorted(SUPPORTED_EXTENSIONS | SUPPORTED_IMAGE_EXTENSIONS)
        raise HTTPException(status_code=415, detail=f"Unsupported file type. Accepted: {', '.join(accepted)}")

    data = await file.read()
    if len(data) > config.MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Max size is {config.MAX_UPLOAD_BYTES // (1024 * 1024)} MB.",
        )
    if not data:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    # --- Image attachment: store the blob for vision-capable models, skip
    # text extraction / RAG chunking entirely (item 18: keep image
    # understanding separate from document RAG). ---
    if is_image_ext:
        image_mime = sniff_image_mime(data)
        if not image_mime:
            raise HTTPException(status_code=422, detail="File has an image extension but its contents are not a recognized image format.")

        doc_id = store.create_document(name=filename, mime_type=image_mime, size=len(data), kind="image")
        store.store_image_blob(doc_id, image_mime, base64.b64encode(data).decode("ascii"))

        return {"id": doc_id, "name": filename, "type": image_mime, "size": len(data), "status": "ready"}

    # --- Document: extract text, chunk, embed, index for RAG. ---
    doc_id = store.create_document(name=filename, mime_type=file.content_type or "application/octet-stream", size=len(data), kind="text")

    try:
        text = extract_text(data, filename)
    except ValueError as exc:
        store.mark_document_error(doc_id, str(exc))
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:  # noqa: BLE001
        store.mark_document_error(doc_id, "Failed to process document.")
        raise HTTPException(status_code=500, detail="Failed to process document.") from exc

    try:
        await process_and_store_document(doc_id, text)
    except Exception as exc:  # noqa: BLE001
        store.mark_document_error(doc_id, "Failed to index document for retrieval.")
        raise HTTPException(status_code=500, detail="Failed to index document for retrieval.") from exc

    doc = store.get_document(doc_id)
    if not doc or doc["status"] != "ready":
        raise HTTPException(status_code=500, detail=(doc or {}).get("error") or "Document processing failed.")

    return {
        "id": doc_id,
        "name": filename,
        "type": file.content_type or "application/octet-stream",
        "size": len(data),
        "status": "ready",
    }


@router.delete("/documents/{document_id}")
async def delete_document(document_id: str):
    doc = store.get_document(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    store.delete_document(document_id)
    return {"success": True}
