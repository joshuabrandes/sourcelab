import logging
from pathlib import Path

import fitz
from bs4 import BeautifulSoup
from markdownify import markdownify
from marker.config.parser import ConfigParser
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
from marker.output import json_to_html
from marker.renderers.json import JSONBlockOutput, JSONOutput

from sidecar.extractors.utils import markdown_to_elements, utc_timestamp
from sidecar.models import ContentType, DocumentElement, DocumentMetadata, ElementType, ExtractedDocument

SUPPORTED_EXTENSIONS = {".pdf": ContentType.pdf}

_logger = logging.getLogger(__name__)
_model_dict: dict | None = None

_SKIPPED_MARKER_BLOCK_TYPES = {"PageHeader", "PageFooter"}
_MARKER_ELEMENT_TYPES = {
    "SectionHeader": ElementType.heading,
    "Table": ElementType.table,
    "TableGroup": ElementType.table,
    "Form": ElementType.table,
    "Code": ElementType.code,
    "ListGroup": ElementType.list,
    "ListItem": ElementType.list,
    "Picture": ElementType.image,
    "PictureGroup": ElementType.image,
    "Figure": ElementType.image,
    "FigureGroup": ElementType.image,
}


def extract_pdf_document(source_id: str, file_path: str) -> ExtractedDocument:
    path = Path(file_path).expanduser().resolve()
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"PDF file not found at {path}")
    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file type: {path.suffix}")

    try:
        elements, page_count, language = _extract_with_marker(path)
    except Exception as exc:
        _logger.warning("Marker extraction failed for %s; using PyMuPDF fallback: %s", path, exc)
        elements, page_count, language = _extract_with_pymupdf(path)

    return ExtractedDocument(
        sourceId=source_id,
        title=path.stem,
        language=language,
        contentType=ContentType.pdf,
        metadata=DocumentMetadata(extractedAt=utc_timestamp(), pageCount=page_count),
        elements=elements,
    )


def _extract_with_marker(path: Path) -> tuple[list[DocumentElement], int, str | None]:
    options = {
        "output_format": "json",
        "force_ocr": False,
        "ocr_all_pages": False,
    }
    config_parser = ConfigParser(options)
    converter = PdfConverter(
        artifact_dict=_get_model_dict(),
        config=config_parser.generate_config_dict(),
        renderer=config_parser.get_renderer(),
        processor_list=config_parser.get_processors(),
        llm_service=config_parser.get_llm_service(),
    )
    rendered = converter(str(path))
    if not isinstance(rendered, JSONOutput):
        raise TypeError(f"Expected Marker JSONOutput, received {type(rendered).__name__}")

    elements = _marker_output_to_elements(rendered)
    language = _first_language(rendered.metadata)
    return elements, len(rendered.children), language


def _get_model_dict() -> dict:
    global _model_dict
    if _model_dict is None:
        _model_dict = create_model_dict()
    return _model_dict


def _marker_output_to_elements(output: JSONOutput) -> list[DocumentElement]:
    elements: list[DocumentElement] = []
    for page_number, page_block in enumerate(output.children, start=1):
        for block in page_block.children or []:
            _append_marker_block(elements, block, page_number)

    if elements:
        return elements
    return [DocumentElement(type=ElementType.paragraph, content="", position=0)]


def _append_marker_block(
    elements: list[DocumentElement],
    block: JSONBlockOutput,
    page_number: int,
) -> None:
    if block.block_type in _SKIPPED_MARKER_BLOCK_TYPES:
        return

    element_type = _MARKER_ELEMENT_TYPES.get(block.block_type)
    if element_type is None and block.children:
        for child in block.children:
            _append_marker_block(elements, child, page_number)
        return
    if element_type is None:
        element_type = ElementType.paragraph

    html = json_to_html(block)
    content, level = _marker_block_content(block, html, element_type)
    if not content and element_type != ElementType.image:
        return

    metadata = {
        "bbox": block.bbox,
        "polygon": block.polygon,
        "markerBlockId": block.id,
        "markerBlockType": block.block_type,
    }
    elements.append(
        DocumentElement(
            type=element_type,
            content=content or "[Image]",
            page=page_number,
            level=level,
            position=len(elements),
            metadata=metadata,
        )
    )


def _marker_block_content(
    block: JSONBlockOutput,
    html: str,
    element_type: ElementType,
) -> tuple[str, int | None]:
    soup = BeautifulSoup(html, "html.parser")
    if element_type == ElementType.heading:
        heading = soup.find(["h1", "h2", "h3", "h4", "h5", "h6"])
        level = int(heading.name[1]) if heading is not None else 2
        return soup.get_text(" ", strip=True), level
    if element_type in {ElementType.table, ElementType.list}:
        return markdownify(html, heading_style="ATX").strip(), None
    if element_type == ElementType.code:
        return soup.get_text("\n", strip=True), None
    if element_type == ElementType.image:
        converted = markdownify(html, heading_style="ATX").strip()
        if converted:
            return converted, None
        image_names = list((block.images or {}).keys())
        if image_names:
            return "\n".join(f"![Image]({name})" for name in image_names), None
        return "[Image]", None
    return soup.get_text(" ", strip=True), None


def _extract_with_pymupdf(path: Path) -> tuple[list[DocumentElement], int, str | None]:
    elements: list[DocumentElement] = []
    with fitz.open(str(path)) as document:
        for page_number, page in enumerate(document, start=1):
            page_text = page.get_text("text", sort=True)
            page_elements = markdown_to_elements(
                page_text,
                page=page_number,
                position_offset=len(elements),
            )
            elements.extend(page_elements)
        return elements, document.page_count, None


def _extract_elements(raw_text: str) -> list[DocumentElement]:
    return markdown_to_elements(raw_text)


def _first_language(metadata: dict) -> str | None:
    languages = metadata.get("languages")
    if isinstance(languages, list) and languages and isinstance(languages[0], str):
        return languages[0]
    if isinstance(languages, str):
        return languages
    return None
