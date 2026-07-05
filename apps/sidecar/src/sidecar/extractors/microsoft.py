from pathlib import Path

from sidecar.extractors.docx import extract_docx_document
from sidecar.extractors.pptx import extract_pptx_document
from sidecar.models import ExtractedDocument

SUPPORTED_EXTENSIONS = {".docx", ".pptx"}


def extract_office_document(source_id: str, file_path: str) -> ExtractedDocument:
    suffix = Path(file_path).suffix.lower()
    if suffix == ".docx":
        return extract_docx_document(source_id, file_path)
    if suffix == ".pptx":
        return extract_pptx_document(source_id, file_path)
    raise ValueError(f"Unsupported file type: {suffix}")
