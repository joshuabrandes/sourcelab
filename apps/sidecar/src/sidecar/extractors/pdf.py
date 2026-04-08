import re
from datetime import datetime, UTC
from pathlib import Path

import fitz
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
from marker.output import text_from_rendered

from sidecar.models import ContentType, ExtractedDocument, DocumentElement, ElementType, DocumentMetadata

SUPPORTED_TEXT_EXTENSIONS = {
    ".pdf": ContentType.pdf
}


def extract_pdf_document(source_id: str, file_path: str) -> ExtractedDocument:
    """
    Extracts text from a PDF file and returns an ExtractedDocument object.

    Args:
        source_id (str): The unique identifier of the source document.
        file_path (str): The path to the PDF file to be extracted.

    Returns:
        ExtractedDocument: An object containing the extracted text and metadata.
    """
    path = Path(file_path).expanduser().resolve()

    if not path.exists():
        raise FileNotFoundError(f"PDF file not found at {path}")

    content_type = SUPPORTED_TEXT_EXTENSIONS.get(path.suffix.lower())
    if content_type is None:
        raise ValueError(f"Unsupported file type: {path.suffix}")

    raw_text, page_count, language = _get_text_from_pdf(path)
    elements = _extract_elements(raw_text)
    metadata = DocumentMetadata(extractedAt=_timestamp(), pageCount=page_count)

    return ExtractedDocument(
        sourceId=source_id,
        title=path.stem,
        language=language,
        contentType=content_type,
        metadata=metadata,
        elements=elements,
    )


# returns test and number of pages
def _get_text_from_pdf(path: Path) -> tuple[str, int, str | None]:
    """
    Extracts text content and page count from a PDF file.

    This function attempts to extract text from the given PDF file.
    If the primary extraction method fails, it falls back to a secondary,
    faster extraction approach.

    Args:
        path: A Path object representing the location of the PDF file.
        :type path: Path
    Returns:
        A tuple containing the extracted text as a string and the total number of pages in the PDF.
        :rtype: tuple[str, int, str | None]
    """
    try:
        return _get_md_from_pdf(path)
    except Exception:
        return _extract_with_pymupdf(path)  # faster fallback


_model_dict: dict | None = None


def _get_model_dict() -> dict:
    global _model_dict
    if _model_dict is None:
        _model_dict = create_model_dict()
    return _model_dict


def _get_md_from_pdf(path: Path) -> tuple[str, int, str | None]:
    """
    Extracts text from a PDF file and returns it as Markdown.

    Args:
        path (Path): The path to the PDF file.

    Returns:
        tuple[str, int, str | None]: The extracted text as Markdown, the total number of pages in the PDF, and the suspected language.
    """
    converter = PdfConverter(
        artifact_dict=_get_model_dict(),
        config={
            "output_format": "markdown",
            "force_ocr": False,  # lets merker decide whether to use OCR
            "ocr_all_pages": False
        }
    )
    rendered = converter(str(path))
    text, _, _ = text_from_rendered(rendered)
    language = rendered.metadata.get("languages", [None])[0]

    doc = fitz.open(str(path))
    num_pages = doc.page_count
    doc.close()
    return text, num_pages, language if language is not None else None


def _extract_with_pymupdf(path: Path) -> tuple[str, int, str | None]:
    """
    Extracts text from a PDF file using PyMuPDF.

    Args:
        path (Path): The path to the PDF file.

    Returns:
        tuple[str, int, str | None]: The extracted text as Markdown, the total number of pages in the PDF, and the suspected language.
    """
    doc = fitz.open(str(path))
    text = "\n\n".join(page.get_text("markdown") for page in doc)
    page_count = doc.page_count
    doc.close()
    return text, page_count, None


def _extract_elements(raw_text: str) -> list[DocumentElement]:
    """
    Parses Markdown-formatted text (as produced by marker) into typed DocumentElements.

    Recognized patterns:
    - Headings      : lines starting with one or more `#`
    - Images        : Markdown image syntax ![alt](url)
    - Code blocks   : fenced blocks ```...```
    - Tables        : blocks whose first non-empty line starts with `|`
    - Lists         : blocks whose lines start with `-`, `*`, `+` or a digit followed by `.`/`)`
    - Paragraphs    : everything else
    """
    stripped = raw_text.strip()
    if not stripped:
        return [DocumentElement(type=ElementType.paragraph, content="", position=0)]

    elements: list[DocumentElement] = []
    position = 0

    # Split on blank lines while preserving fenced code blocks
    # We manually walk through to handle multi-line fenced blocks correctly
    blocks: list[str] = []
    current_lines: list[str] = []
    in_fence = False

    for line in stripped.splitlines():
        if re.match(r"^```", line):
            in_fence = not in_fence
            current_lines.append(line)
            if not in_fence:
                # closing fence – end of code block
                blocks.append("\n".join(current_lines))
                current_lines = []
        elif not in_fence and line.strip() == "":
            if current_lines:
                blocks.append("\n".join(current_lines))
                current_lines = []
        else:
            current_lines.append(line)

    if current_lines:
        blocks.append("\n".join(current_lines))

    image_pattern = re.compile(r"^!\[.*?\]\(.*?\)$")
    list_line_pattern = re.compile(r"^(\s*([-*+]|\d+[.)]) )")

    for block in blocks:
        block = block.strip()
        if not block:
            continue

        # --- Code block ---
        if block.startswith("```"):
            # Strip fences and optional language tag
            inner = re.sub(r"^```[^\n]*\n?", "", block)
            inner = re.sub(r"\n?```$", "", inner)
            elements.append(
                DocumentElement(
                    type=ElementType.code,
                    content=inner.strip(),
                    position=position,
                )
            )
            position += 1
            continue

        # --- Heading ---
        if block.startswith("#"):
            level = len(block) - len(block.lstrip("#"))
            heading_text = block.lstrip("#").strip()
            elements.append(
                DocumentElement(
                    type=ElementType.heading,
                    content=heading_text or block,
                    level=max(1, min(level, 6)),
                    position=position,
                )
            )
            position += 1
            continue

        # --- Image (single-line Markdown image) ---
        if image_pattern.match(block):
            elements.append(
                DocumentElement(
                    type=ElementType.image,
                    content=block,
                    position=position,
                )
            )
            position += 1
            continue

        # --- Table (pipe-delimited) ---
        first_line = block.splitlines()[0].strip()
        if first_line.startswith("|"):
            elements.append(
                DocumentElement(
                    type=ElementType.table,
                    content=block,
                    position=position,
                )
            )
            position += 1
            continue

        # --- List ---
        lines = block.splitlines()
        if any(list_line_pattern.match(line) for line in lines):
            elements.append(
                DocumentElement(
                    type=ElementType.list,
                    content=block,
                    position=position,
                )
            )
        position += 1
        continue

        # --- Paragraph (fallback) ---
        elements.append(
            DocumentElement(
                type=ElementType.paragraph,
                content=block,
                position=position,
            )
        )
        position += 1

    return elements


def _timestamp() -> str:
    return datetime.now(UTC).isoformat()
