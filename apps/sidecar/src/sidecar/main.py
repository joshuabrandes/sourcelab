import uvicorn
from fastapi import FastAPI, HTTPException

from sidecar.chunking import chunk_elements
from sidecar.extractors import (
    extract_html_document,
    extract_image_document,
    extract_office_document,
    extract_pdf_document,
    extract_plain_text_document,
    extract_url_document,
    extract_youtube_document,
)
from sidecar.models import ChunkRequest, ChunkResponse, ContentType, ExtractFileRequest, ExtractedDocument

app = FastAPI(title="SourceLab Sidecar", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
def ready() -> dict[str, str]:
    return {"status": "ready"}


@app.post("/extract/file", response_model=ExtractedDocument)
def extract_file(request: ExtractFileRequest) -> ExtractedDocument:
    try:
        return _dispatch_extract(request)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/chunk", response_model=ChunkResponse)
def chunk_document(request: ChunkRequest) -> ChunkResponse:
    try:
        chunks = chunk_elements(
            source_id=request.sourceId,
            elements=request.elements,
            chunk_size=request.chunkSize,
            chunk_overlap=request.chunkOverlap,
        )
        return ChunkResponse(sourceId=request.sourceId, chunks=chunks)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _dispatch_extract(request: ExtractFileRequest) -> ExtractedDocument:
    if request.contentType in (ContentType.md, ContentType.txt):
        file_path = _require_file_path(request)
        return extract_plain_text_document(source_id=request.sourceId, file_path=file_path)

    if request.contentType == ContentType.pdf:
        file_path = _require_file_path(request)
        return extract_pdf_document(source_id=request.sourceId, file_path=file_path)

    if request.contentType in (ContentType.docx, ContentType.pptx):
        file_path = _require_file_path(request)
        return extract_office_document(source_id=request.sourceId, file_path=file_path)

    if request.contentType == ContentType.html:
        file_path = _require_file_path(request)
        return extract_html_document(source_id=request.sourceId, file_path=file_path)

    if request.contentType == ContentType.image:
        file_path = _require_file_path(request)
        return extract_image_document(source_id=request.sourceId, file_path=file_path)

    if request.contentType == ContentType.url:
        source_url = _require_source_url(request)
        return extract_url_document(source_id=request.sourceId, url=source_url)

    if request.contentType == ContentType.youtube:
        source_url = _require_source_url(request)
        return extract_youtube_document(source_id=request.sourceId, url=source_url)

    raise ValueError(f"Unsupported content type: {request.contentType}")


def _require_file_path(request: ExtractFileRequest) -> str:
    if not request.filePath:
        raise ValueError(f"filePath is required for contentType '{request.contentType}'")
    return request.filePath


def _require_source_url(request: ExtractFileRequest) -> str:
    if not request.sourceUrl:
        raise ValueError(f"sourceUrl is required for contentType '{request.contentType}'")
    return request.sourceUrl


def main():
    uvicorn.run("sidecar.main:app", host="127.0.0.1", port=8001, reload=False)
