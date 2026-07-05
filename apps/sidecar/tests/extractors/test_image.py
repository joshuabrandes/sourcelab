from PIL import Image

from sidecar.extractors.image import _ocr_lines_to_elements, extract_image_document
from sidecar.models import ContentType, ElementType


def test_ocr_elements_include_geometry_and_contiguous_positions():
    lines = [
        {"text": "Large heading", "bbox": [0, 0, 200, 40], "confidence": 0.9},
        {"text": "First paragraph line", "bbox": [0, 100, 200, 115], "confidence": 0.8},
        {"text": "Second paragraph line", "bbox": [0, 118, 200, 133], "confidence": 0.7},
    ]

    elements = _ocr_lines_to_elements(lines)

    assert [element.type for element in elements] == [ElementType.heading, ElementType.paragraph]
    assert [element.position for element in elements] == [0, 1]
    assert elements[0].metadata["bbox"] == [0, 0, 200, 40]
    assert elements[1].metadata["confidence"] == 0.75


def test_extract_image_document_uses_local_ocr(tmp_path, mocker):
    path = tmp_path / "scan.png"
    Image.new("RGB", (120, 80), "white").save(path)
    mocker.patch(
        "sidecar.extractors.image._run_ocr",
        return_value=[{"text": "Scanned text", "bbox": [0, 0, 100, 10], "confidence": 0.9}],
    )

    extracted = extract_image_document("source-1", str(path))

    assert extracted.contentType == ContentType.image
    assert extracted.metadata.imageWidth == 120
    assert extracted.metadata.imageHeight == 80
    assert extracted.elements[0].content == "Scanned text"
