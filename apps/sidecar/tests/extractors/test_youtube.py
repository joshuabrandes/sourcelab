"""
Tests for the YouTube extractor.

External I/O (YouTubeTranscriptApi + httpx) is mocked so tests run offline.
Pure helper functions are tested directly without mocking.
"""

import pytest

from sidecar.extractors.youtube import (
    _extract_video_id,
    _format_timestamp,
    _transcript_to_elements,
    extract_youtube_document,
)
from sidecar.models import ContentType, ElementType

RICKROLL_ID = "dQw4w9WgXcQ"
RICKROLL_URL = f"https://www.youtube.com/watch?v={RICKROLL_ID}"

# Fake transcript entries (text, start time in seconds, duration)
RICKROLL_TRANSCRIPT = [
    {"text": "We're no strangers to love", "start": 0.0, "duration": 3.5},
    {"text": "You know the rules and so do I", "start": 3.5, "duration": 3.5},
    {"text": "A full commitment's what I'm thinking of", "start": 7.0, "duration": 3.5},
    {"text": "You wouldn't get this from any other guy", "start": 10.5, "duration": 3.5},
    {"text": "I just wanna tell you how I'm feeling", "start": 14.0, "duration": 3.5},
    {"text": "Gotta make you understand", "start": 17.5, "duration": 3.5},
    # chorus starts at 62s → triggers a new segment (>60s gap from 0)
    {"text": "Never gonna give you up", "start": 62.0, "duration": 3.0},
    {"text": "Never gonna let you down", "start": 65.0, "duration": 3.0},
    {"text": "Never gonna run around and desert you", "start": 68.0, "duration": 3.5},
    {"text": "Never gonna make you cry", "start": 71.5, "duration": 3.0},
    {"text": "Never gonna say goodbye", "start": 74.5, "duration": 3.0},
    {"text": "Never gonna tell a lie and hurt you", "start": 77.5, "duration": 3.5},
]


# ── pure helpers ──────────────────────────────────────────────────────────────

def test_extract_video_id_standard_url():
    assert _extract_video_id(RICKROLL_URL) == RICKROLL_ID


def test_extract_video_id_short_url():
    assert _extract_video_id(f"https://youtu.be/{RICKROLL_ID}") == RICKROLL_ID


def test_extract_video_id_embed_url():
    assert _extract_video_id(f"https://www.youtube.com/embed/{RICKROLL_ID}") == RICKROLL_ID


def test_extract_video_id_invalid_url():
    assert _extract_video_id("https://example.com/not-a-video") is None


@pytest.mark.parametrize("seconds,expected", [
    (0.0, "0:00"),
    (61.0, "1:01"),
    (3661.0, "1:01:01"),
    (62.0, "1:02"),
])
def test_format_timestamp(seconds, expected):
    assert _format_timestamp(seconds) == expected


def test_transcript_to_elements_empty():
    elements = _transcript_to_elements([])
    assert len(elements) == 1
    assert elements[0].type == ElementType.paragraph
    assert elements[0].content == ""


def test_transcript_to_elements_segments_split_at_60s():
    elements = _transcript_to_elements(RICKROLL_TRANSCRIPT)
    # First segment: 0–17.5s, second segment: starts at 62s
    assert len(elements) == 2


def test_transcript_first_segment_contains_intro():
    elements = _transcript_to_elements(RICKROLL_TRANSCRIPT)
    assert "no strangers to love" in elements[0].content


def test_transcript_second_segment_contains_chorus():
    elements = _transcript_to_elements(RICKROLL_TRANSCRIPT)
    assert "Never gonna give you up" in elements[1].content


def test_transcript_elements_have_timestamps():
    elements = _transcript_to_elements(RICKROLL_TRANSCRIPT)
    assert elements[0].content.startswith("[0:00]")
    assert elements[1].content.startswith("[1:02]")


def test_transcript_positions_are_contiguous():
    elements = _transcript_to_elements(RICKROLL_TRANSCRIPT)
    for i, el in enumerate(elements):
        assert el.position == i


# ── full extractor with mocks ─────────────────────────────────────────────────

class FakeTranscriptEntry:
    def __init__(self, text, start, duration):
        self.text = text
        self.start = start
        self.duration = duration


class FakeTranscript:
    language_code = "en"

    def fetch(self):
        return [FakeTranscriptEntry(**e) for e in RICKROLL_TRANSCRIPT]


class FakeTranscriptList:
    def find_manually_created_transcript(self, languages):
        raise Exception("no manual transcript")

    def find_generated_transcript(self, languages):
        return FakeTranscript()


def test_extract_youtube_document(mocker):
    # Mock the transcript API
    mocker.patch(
        "sidecar.extractors.youtube._ytt_api.list",
        return_value=FakeTranscriptList(),
    )

    # Mock the httpx metadata call
    mock_response = mocker.MagicMock()
    mock_response.json.return_value = {
        "title": "Rick Astley - Never Gonna Give You Up (Official Music Video)",
        "author_name": "Rick Astley",
    }
    mock_response.raise_for_status.return_value = None
    mock_client = mocker.MagicMock()
    mock_client.__enter__ = mocker.MagicMock(return_value=mock_client)
    mock_client.__exit__ = mocker.MagicMock(return_value=False)
    mock_client.get.return_value = mock_response
    mocker.patch("sidecar.extractors.youtube.httpx.Client", return_value=mock_client)

    doc = extract_youtube_document("src-rick", RICKROLL_URL)

    assert doc.sourceId == "src-rick"
    assert doc.contentType == ContentType.youtube
    assert doc.title == "Rick Astley - Never Gonna Give You Up (Official Music Video)"
    assert doc.metadata.author == "Rick Astley"
    assert doc.language == "en"
    assert len(doc.elements) == 2


def test_extract_youtube_invalid_url(mocker):
    with pytest.raises(ValueError, match="Could not extract YouTube video ID"):
        extract_youtube_document("src-x", "https://example.com/not-youtube")


def test_extract_youtube_no_transcript(mocker):
    from youtube_transcript_api import NoTranscriptFound, TranscriptsDisabled

    mock_list = mocker.MagicMock()
    mock_list.find_manually_created_transcript.side_effect = Exception("no manual")
    mock_list.find_generated_transcript.side_effect = NoTranscriptFound(
        RICKROLL_ID, ["en"], {}
    )
    mocker.patch("sidecar.extractors.youtube._ytt_api.list", return_value=mock_list)

    with pytest.raises(ValueError, match="No transcript available"):
        extract_youtube_document("src-x", RICKROLL_URL)