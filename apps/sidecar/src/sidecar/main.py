import uvicorn
from fastapi import FastAPI, HTTPException

from sidecar.extractors import extract_plain_text_document
from sidecar.models import ExtractFileRequest, ExtractedDocument

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
        return extract_plain_text_document(
            source_id=request.sourceId,
            file_path=request.filePath,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def main():
    uvicorn.run("sidecar.main:app", host="127.0.0.1", port=8001, reload=False)
