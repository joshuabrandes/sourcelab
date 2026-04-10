from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

import httpx
import trafilatura
from bs4 import BeautifulSoup

from sidecar.models import ContentType, DocumentElement, DocumentMetadata, ExtractedDocument, ElementType

SUPPORTED_EXTENSIONS = {
    ".html": ContentType.html,
    ".htm": ContentType.html,
}

def extract_html_document(source_id: str, file_path: str) -> ExtractedDocument:
    path = Path(file_path).expanduser().resolve()
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"File not found: {path}")

    raw_html = path.read_text(encoding="utf-8")
    title, metadata, elements = _process_html(raw_html, source_url=None)

    return ExtractedDocument(
        sourceId=source_id,
        title=title or path.stem,
        language=None,
        contentType=ContentType.html,
        metadata=metadata,
        elements=elements,
    )


def extract_url_document(source_id: str, url: str) -> ExtractedDocument:
    try:
        raw_html = _fetch_url(url)
    except httpx.RequestError as e:
        raise ValueError(f"Failed to fetch URL: {url}") from e
    title, metadata, elements = _process_html(raw_html, source_url=url)

    return ExtractedDocument(
        sourceId=source_id,
        title=title or _hostname_from_url(url),
        language=None,
        contentType=ContentType.url,
        metadata=metadata,
        elements=elements,
    )


def _fetch_url(url: str) -> str:
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; SourceLab/1.0)"}
        with httpx.Client(follow_redirects=True, timeout=30.0) as client:
            response = client.get(url, headers=headers)
    except httpx.RequestError as e:
        raise ValueError(f"Failed to fetch URL: {url}") from e
    response.raise_for_status()
    return response.text


def _process_html(
        raw_html: str, source_url: str | None
) -> tuple[str | None, DocumentMetadata, list[DocumentElement]]:
    soup = BeautifulSoup(raw_html, "html.parser")
    title = _extract_title(soup)
    author = _extract_meta(soup, ["author", "article:author"])

    # trafilatura strips nav/footer/ads and returns clean markdown
    markdown_content = trafilatura.extract(
        raw_html,
        url=source_url,
        output_format="markdown",
        include_tables=True,
        include_comments=False,
        favor_recall=True,
    )

    if not markdown_content:
        body = soup.find("body")
        markdown_content = body.get_text(separator="\n\n") if body else ""

    metadata = DocumentMetadata(extractedAt=_timestamp(), pageCount=1, author=author)
    return title, metadata, _markdown_to_elements(markdown_content)


def _extract_title(soup: BeautifulSoup) -> str | None:
    candidates = [
        soup.find("meta", property="og:title"),
        soup.find("meta", attrs={"name": "twitter:title"}),
        soup.find("title"),
        soup.find("h1"),
    ]
    for tag in candidates:
        if not tag:
            continue
        text = tag.get("content") or tag.get_text()
        if text and text.strip():
            return text.strip()
    return None


def _extract_meta(soup: BeautifulSoup, names: list[str]) -> str | None:
    for name in names:
        tag = soup.find("meta", attrs={"name": name}) or soup.find("meta", property=name)
        if tag and tag.get("content"):
            return tag["content"].strip()
    return None


def _markdown_to_elements(text: str) -> list[DocumentElement]:
    stripped = text.strip()
    if not stripped:
        return [DocumentElement(type=ElementType.paragraph, content="", position=0)]

    elements: list[DocumentElement] = []
    position = 0

    for block in _split_markdown_blocks(stripped):
        if block.startswith("```") or block.startswith("~~~"):
            elements.append(DocumentElement(type=ElementType.code, content=block, position=position))
            position += 1
            continue

        lines = block.splitlines()
        if len(lines) >= 2 and lines[0].startswith("|") and set(lines[1].replace(" ", "")) <= {"|", "-", ":"}:
            elements.append(DocumentElement(type=ElementType.table, content=block, position=position))
            position += 1
            continue

        if block.startswith("#"):
            first_line = lines[0]
            level = len(first_line) - len(first_line.lstrip("#"))
            heading_text = first_line.lstrip("#").strip()
            elements.append(
                DocumentElement(
                    type=ElementType.heading,
                    content=heading_text or first_line,
                    level=max(1, min(level, 6)),
                    position=position,
                )
            )
            position += 1
            continue

        elements.append(DocumentElement(type=ElementType.paragraph, content=block.strip(), position=position))
        position += 1

    return elements


def _split_markdown_blocks(text: str) -> list[str]:
    """Split on blank lines but keep fenced code blocks intact."""
    blocks: list[str] = []
    current: list[str] = []
    in_fence = False
    fence_marker = ""

    for line in text.splitlines():
        stripped = line.strip()

        if not in_fence and (stripped.startswith("```") or stripped.startswith("~~~")):
            if current:
                blocks.append("\n".join(current))
                current = []
            in_fence = True
            fence_marker = stripped[:3]
            current.append(line)
            continue

        if in_fence:
            current.append(line)
            if stripped == fence_marker:
                blocks.append("\n".join(current))
                current = []
                in_fence = False
            continue

        if not stripped:
            if current:
                blocks.append("\n".join(current))
                current = []
        else:
            current.append(line)

    if current:
        blocks.append("\n".join(current))

    return [b for b in blocks if b.strip()]


def _hostname_from_url(url: str) -> str:
    return urlparse(url).hostname or url


def _timestamp() -> str:
    return datetime.now(UTC).isoformat()
