from datetime import UTC, datetime
from pathlib import Path

from sidecar.models import ContentType, DocumentElement, DocumentMetadata, ExtractedDocument, ElementType

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
    metadata = DocumentMetadata(extractedAt=_timestamp(), pageCount=1)

    return ExtractedDocument(
        sourceId=source_id,
        title=path.stem or path.name,
        language=None,
        contentType=content_type,
        metadata=metadata,
        elements=elements,
    )


def _extract_elements(raw_text: str) -> list[DocumentElement]:
    stripped = raw_text.strip()
    if not stripped:
        return [DocumentElement(type=ElementType.paragraph, content="", position=0)]

    blocks = [block.strip() for block in stripped.split("\n\n") if block.strip()]
    elements: list[DocumentElement] = []

    for position, block in enumerate(blocks):
        if block.startswith("#"):
            heading_text = block.lstrip("#").strip()
            level = len(block) - len(block.lstrip("#"))
            elements.append(
                DocumentElement(
                    type=ElementType.heading,
                    content=heading_text or block,
                    level=max(1, level),
                    position=position,
                )
            )
            continue

        elements.append(
            DocumentElement(
                type=ElementType.paragraph,
                content=block,
                position=position,
            )
        )

    return elements


def _timestamp() -> str:
    return datetime.now(UTC).isoformat()
