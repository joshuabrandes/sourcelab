import pytest

from sidecar.main import _dispatch_extract
from sidecar.models import ContentType, ExtractFileRequest, ExtractedDocument


def _dummy_doc() -> ExtractedDocument:
    return ExtractedDocument.model_validate(
        {
            "sourceId": "src-1",
            "title": "dummy",
            "contentType": "txt",
            "metadata": {"extractedAt": "2026-01-01T00:00:00Z"},
            "elements": [{"type": "paragraph", "content": "x", "position": 0}],
        }
    )


def test_dispatch_plain_text_calls_plain_text_extractor(mocker):
    mock = mocker.patch("sidecar.main.extract_plain_text_document", return_value=_dummy_doc())
    request = ExtractFileRequest(sourceId="src-1", contentType=ContentType.txt, filePath="/tmp/a.txt")

    _dispatch_extract(request)

    mock.assert_called_once_with(source_id="src-1", file_path="/tmp/a.txt")


def test_dispatch_url_calls_url_extractor(mocker):
    mock = mocker.patch("sidecar.main.extract_url_document", return_value=_dummy_doc())
    request = ExtractFileRequest(
        sourceId="src-1",
        contentType=ContentType.url,
        sourceUrl="https://example.com",
    )

    _dispatch_extract(request)

    mock.assert_called_once_with(source_id="src-1", url="https://example.com")


def test_dispatch_youtube_calls_youtube_extractor(mocker):
    mock = mocker.patch("sidecar.main.extract_youtube_document", return_value=_dummy_doc())
    request = ExtractFileRequest(
        sourceId="src-1",
        contentType=ContentType.youtube,
        sourceUrl="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    )

    _dispatch_extract(request)

    mock.assert_called_once()


def test_dispatch_requires_file_path_for_file_types():
    request = ExtractFileRequest(sourceId="src-1", contentType=ContentType.pdf)

    with pytest.raises(ValueError, match="filePath is required"):
        _dispatch_extract(request)


def test_dispatch_requires_source_url_for_url_types():
    request = ExtractFileRequest(sourceId="src-1", contentType=ContentType.url)

    with pytest.raises(ValueError, match="sourceUrl is required"):
        _dispatch_extract(request)
