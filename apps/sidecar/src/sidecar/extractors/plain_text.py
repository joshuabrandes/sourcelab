from pathlib import Path

from sidecar.extractors.utils import markdown_to_elements, utc_timestamp
from sidecar.models import ContentType, DocumentElement, DocumentMetadata, ExtractedDocument

SUPPORTED_TEXT_EXTENSIONS = {
    ".md": ContentType.md,
    ".markdown": ContentType.md,
    ".txt": ContentType.txt,
}


def extract_plain_text_document(source_id: str, file_path: str) -> ExtractedDocument:
    path = Path(file_path).expanduser().resolve()

    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"File not found: {path}")

    content_type = SUPPORTED_TEXT_EXTENSIONS.get(path.suffix.lower())
    if content_type is None:
        raise ValueError(f"Unsupported file type: {path.suffix or '<none>'}")

    raw_text = path.read_text(encoding="utf-8")
    elements = _extract_elements(raw_text)
    metadata = DocumentMetadata(extractedAt=utc_timestamp(), pageCount=1)

    return ExtractedDocument(
        sourceId=source_id,
        title=path.stem or path.name,
        language=None,
        contentType=content_type,
        metadata=metadata,
        elements=elements,
    )


def _extract_elements(raw_text: str) -> list[DocumentElement]:
    return markdown_to_elements(raw_text)
