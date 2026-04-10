import re
from datetime import UTC, datetime

import httpx
from youtube_transcript_api import NoTranscriptFound, TranscriptsDisabled, YouTubeTranscriptApi

from sidecar.models import ContentType, DocumentElement, DocumentMetadata, ExtractedDocument, ElementType

_VIDEO_ID_PATTERN = re.compile(
    r"(?:v=|youtu\.be/|embed/|shorts/|live/|/v/)([A-Za-z0-9_-]{11})"
)
_SEGMENT_DURATION_SECONDS = 60
_PREFERRED_LANGUAGES = ["en", "de", "fr", "es", "ja", "ko"]

_ytt_api = YouTubeTranscriptApi()


def extract_youtube_document(source_id: str, url: str) -> ExtractedDocument:
    video_id = _extract_video_id(url)
    if not video_id:
        raise ValueError(f"Could not extract YouTube video ID from: {url}")

    entries, language = _fetch_transcript(video_id)
    title, channel = _fetch_video_metadata(video_id)
    elements = _transcript_to_elements(entries)

    metadata = DocumentMetadata(
        extractedAt=_timestamp(),
        pageCount=1,
        author=channel,
        language=language,
    )

    return ExtractedDocument(
        sourceId=source_id,
        title=title or video_id,
        language=language,
        contentType=ContentType.youtube,
        metadata=metadata,
        elements=elements,
    )


def _extract_video_id(url: str) -> str | None:
    match = _VIDEO_ID_PATTERN.search(url)
    return match.group(1) if match else None


def _fetch_transcript(video_id: str) -> tuple[list[dict], str | None]:
    try:
        transcript_list = _ytt_api.list(video_id)

        try:
            transcript = transcript_list.find_manually_created_transcript(_PREFERRED_LANGUAGES)
        except Exception:
            transcript = transcript_list.find_generated_transcript(_PREFERRED_LANGUAGES)

        entries = [
            {"text": e.text, "start": e.start, "duration": e.duration}
            for e in transcript.fetch()
        ]
        return entries, transcript.language_code

    except (TranscriptsDisabled, NoTranscriptFound) as exc:
        raise ValueError(f"No transcript available for video: {video_id}") from exc


def _fetch_video_metadata(video_id: str) -> tuple[str | None, str | None]:
    """Uses YouTube's public oEmbed endpoint -- no API key required."""
    oembed_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(oembed_url)
            response.raise_for_status()
            data = response.json()
            return data.get("title"), data.get("author_name")
    except Exception:
        return None, None


def _transcript_to_elements(entries: list[dict]) -> list[DocumentElement]:
    if not entries:
        return [DocumentElement(type=ElementType.paragraph, content="", position=0)]

    elements: list[DocumentElement] = []
    position = 0
    segment_start: float = entries[0]["start"]
    current_texts: list[str] = []

    for entry in entries:
        start: float = entry["start"]
        text: str = entry["text"].strip().replace("\n", " ")

        if start - segment_start >= _SEGMENT_DURATION_SECONDS and current_texts:
            elements.append(_build_segment_element(current_texts, segment_start, position))
            position += 1
            segment_start = start
            current_texts = [text]
        else:
            current_texts.append(text)

    if current_texts:
        elements.append(_build_segment_element(current_texts, segment_start, position))

    return elements


def _build_segment_element(texts: list[str], start_seconds: float, position: int) -> DocumentElement:
    timestamp = _format_timestamp(start_seconds)
    content = f"[{timestamp}] " + " ".join(texts)
    return DocumentElement(
        type=ElementType.paragraph,
        content=content,
        position=position,
        metadata=None,
    )


def _format_timestamp(seconds: float) -> str:
    total = int(seconds)
    minutes, secs = divmod(total, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours}:{minutes:02d}:{secs:02d}" if hours else f"{minutes}:{secs:02d}"


def _timestamp() -> str:
    return datetime.now(UTC).isoformat()
