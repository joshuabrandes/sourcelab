from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sidecar.models import ContentType, DocumentElement, DocumentMetadata, ExtractedDocument, ElementType

SUPPORTED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp", ".webp"}

# Lazy-loaded surya models -- loading is expensive (~2-4 GB, happens once per process)
_surya_models: dict[str, Any] | None = None


def extract_image_document(source_id: str, file_path: str) -> ExtractedDocument:
    path = Path(file_path).expanduser().resolve()
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"File not found: {path}")
    if path.suffix.lower() not in SUPPORTED_IMAGE_EXTENSIONS:
        raise ValueError(f"Unsupported image format: {path.suffix}")

    ocr_lines = _run_ocr(path)
    elements = _ocr_lines_to_elements(ocr_lines)
    image_size = _read_image_size(path)

    metadata = DocumentMetadata(
        extractedAt=_timestamp(),
        pageCount=1,
        imageWidth=image_size[0],
        imageHeight=image_size[1],
    )

    return ExtractedDocument(
        sourceId=source_id,
        title=path.stem,
        language=None,
        contentType=ContentType.image,
        metadata=metadata,
        elements=elements,
    )


def _get_surya_models() -> dict[str, Any] | None:
    global _surya_models
    if _surya_models is None:
        from surya.detection import DetectionPredictor
        from surya.foundation import FoundationPredictor
        from surya.recognition import RecognitionPredictor

        foundation = FoundationPredictor()
        _surya_models = {
            "det_predictor": DetectionPredictor(),
            "rec_predictor": RecognitionPredictor(foundation),
        }
    return _surya_models


def _run_ocr(path: Path) -> list[dict]:
    from PIL import Image

    models = _get_surya_models()
    image = Image.open(path).convert("RGB")

    predictions = models["rec_predictor"](
        [image],
        det_predictor=models["det_predictor"],
    )

    if not predictions:
        return []

    return [
        {"text": line.text, "bbox": line.bbox, "confidence": line.confidence}
        for line in predictions[0].text_lines
        if line.text.strip() and line.confidence > 0.5
    ]


def _ocr_lines_to_elements(ocr_lines: list[dict]) -> list[DocumentElement]:
    if not ocr_lines:
        return [DocumentElement(type=ElementType.paragraph, content="", position=0)]

    # Sort top-to-bottom, then left-to-right
    sorted_lines = sorted(ocr_lines, key=lambda l: (l["bbox"][1], l["bbox"][0]))
    groups = _group_lines_into_paragraphs(sorted_lines)

    elements: list[DocumentElement] = []
    for position, group in enumerate(groups):
        text = " ".join(line["text"] for line in group).strip()
        if not text:
            continue

        group_bbox = [
            min(l["bbox"][0] for l in group),
            group[0]["bbox"][1],
            max(l["bbox"][2] for l in group),
            group[-1]["bbox"][3],
        ]
        avg_line_height = sum(l["bbox"][3] - l["bbox"][1] for l in group) / len(group)
        is_short_and_tall = len(text) < 80 and avg_line_height > 28 and len(group) <= 2

        element_type = ElementType.heading if is_short_and_tall else ElementType.paragraph
        elements.append(
            DocumentElement(
                type=element_type,
                content=text,
                level=1 if element_type == ElementType.heading else None,
                position=position,
                metadata=None, # {"bbox": group_bbox},
            )
        )

    return elements


def _group_lines_into_paragraphs(lines: list[dict]) -> list[list[dict]]:
    """Groups lines whose vertical gap is smaller than 1.5x the line height."""
    if not lines:
        return []

    groups: list[list[dict]] = [[lines[0]]]

    for line in lines[1:]:
        prev = groups[-1][-1]
        line_height = prev["bbox"][3] - prev["bbox"][1]
        vertical_gap = line["bbox"][1] - prev["bbox"][3]

        if vertical_gap > line_height * 1.5:
            groups.append([line])
        else:
            groups[-1].append(line)

    return groups


def _read_image_size(path: Path) -> tuple[int, int]:
    from PIL import Image
    with Image.open(path) as img:
        return img.size


def _timestamp() -> str:
    return datetime.now(UTC).isoformat()