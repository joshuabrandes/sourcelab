from pathlib import Path
from urllib.parse import urlparse

import httpx
import trafilatura
from bs4 import BeautifulSoup

from sidecar.extractors.utils import markdown_to_elements, utc_timestamp
from sidecar.models import ContentType, DocumentElement, DocumentMetadata, ElementType, ExtractedDocument

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
    raw_html = _fetch_url(url)
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
    except httpx.HTTPError as e:
        raise ValueError(f"Failed to fetch URL: {url}") from e
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as e:
        raise ValueError(f"URL returned HTTP {response.status_code}: {url}") from e
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

    metadata = DocumentMetadata(extractedAt=utc_timestamp(), pageCount=1, author=author)
    elements = _markdown_to_elements(markdown_content)
    if title and not any(element.type == ElementType.heading for element in elements):
        elements.insert(
            0,
            DocumentElement(type=ElementType.heading, content=title, level=1, position=0),
        )
        for position, element in enumerate(elements):
            element.position = position
    return title, metadata, elements


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
    return markdown_to_elements(text)


def _hostname_from_url(url: str) -> str:
    return urlparse(url).hostname or url
