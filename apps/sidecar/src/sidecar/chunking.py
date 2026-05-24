import re
from dataclasses import dataclass

from sidecar.models import ChunkElement, DocumentChunk

UNSPLITTABLE_TYPES = {"table", "code", "image"}


@dataclass
class Heading:
    level: int
    text: str


@dataclass
class ChunkDraft:
    content: str
    token_count: int
    start_element: str
    end_element: str
    heading_context: str | None
    page: int | None


def chunk_elements(
    source_id: str,
    elements: list[ChunkElement],
    chunk_size: int = 512,
    chunk_overlap: int = 64,
) -> list[DocumentChunk]:
    normalized_chunk_size = max(1, chunk_size)
    normalized_overlap = max(0, min(chunk_overlap, normalized_chunk_size - 1))
    sorted_elements = sorted(elements, key=lambda element: element.position)
    heading_stack: list[Heading] = []
    drafts: list[ChunkDraft] = []
    active: ChunkDraft | None = None

    def flush_active() -> None:
        nonlocal active
        if active is not None:
            drafts.append(active)
            active = None

    for element in sorted_elements:
        element_type = element.type.value

        if element_type == "heading":
            flush_active()
            _update_heading_stack(heading_stack, element.level or 1, element.content)
            continue

        heading_context = _format_heading_context(heading_stack)
        pieces = _split_element_content(
            element.content,
            chunk_size=normalized_chunk_size,
            chunk_overlap=normalized_overlap,
            can_split=element_type not in UNSPLITTABLE_TYPES,
        )

        for piece in pieces:
            piece_token_count = estimate_token_count(piece)
            page = element.page

            if (
                active is not None
                and active.heading_context == heading_context
                and active.token_count + piece_token_count <= normalized_chunk_size
            ):
                active.content = _join_chunk_content(active.content, piece)
                active.token_count += piece_token_count
                active.end_element = element.id
                active.page = active.page or page
                continue

            flush_active()
            active = ChunkDraft(
                content=piece,
                token_count=piece_token_count,
                start_element=element.id,
                end_element=element.id,
                heading_context=heading_context,
                page=page,
            )

            if element_type in UNSPLITTABLE_TYPES or piece_token_count >= normalized_chunk_size:
                flush_active()

    flush_active()

    if not drafts and sorted_elements:
        first = sorted_elements[0]
        drafts.append(
            ChunkDraft(
                content=first.content,
                token_count=estimate_token_count(first.content),
                start_element=first.id,
                end_element=first.id,
                heading_context=_format_heading_context(heading_stack),
                page=first.page,
            )
        )

    return [
        DocumentChunk(
            sourceId=source_id,
            content=draft.content,
            tokenCount=draft.token_count,
            startElement=draft.start_element,
            endElement=draft.end_element,
            headingContext=draft.heading_context,
            page=draft.page,
            position=position,
        )
        for position, draft in enumerate(drafts)
    ]


def _update_heading_stack(stack: list[Heading], level: int, text: str) -> None:
    normalized_level = max(1, level)
    while stack and stack[-1].level >= normalized_level:
        stack.pop()
    stack.append(Heading(level=normalized_level, text=text.strip()))


def _format_heading_context(stack: list[Heading]) -> str | None:
    context = " > ".join(heading.text for heading in stack if heading.text)
    return context or None


def _split_element_content(
    content: str,
    *,
    chunk_size: int,
    chunk_overlap: int,
    can_split: bool,
) -> list[str]:
    normalized = content.strip()
    if not normalized:
        return [""]
    if not can_split or estimate_token_count(normalized) <= chunk_size:
        return [normalized]

    sentences = _split_sentences(normalized)
    chunks: list[str] = []
    current = ""
    current_tokens = 0

    for sentence in sentences:
        sentence_tokens = estimate_token_count(sentence)

        if current and current_tokens + sentence_tokens > chunk_size:
            chunks.append(current)
            current = _build_overlap(current, chunk_overlap)
            current_tokens = estimate_token_count(current)

        if not current and sentence_tokens > chunk_size:
            chunks.extend(_split_long_text(sentence, chunk_size, chunk_overlap))
            continue

        current = _join_chunk_content(current, sentence)
        current_tokens = estimate_token_count(current)

    if current:
        chunks.append(current)

    return chunks


def _split_sentences(text: str) -> list[str]:
    matches = re.findall(r"[^.!?\n]+(?:[.!?]+|\n+|$)", text)
    return [sentence.strip() for sentence in matches if sentence.strip()] or [text]


def _split_long_text(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    words = [word for word in re.split(r"\s+", text) if word]
    chunks: list[str] = []
    index = 0

    while index < len(words):
        start = max(0, index)
        current = ""

        while index < len(words):
            next_content = _join_chunk_content(current, words[index])
            if current and estimate_token_count(next_content) > chunk_size:
                break
            current = next_content
            index += 1

        if not current:
            current = words[index]
            index += 1

        chunks.append(current)
        overlap_words = [word for word in re.split(r"\s+", _build_overlap(current, chunk_overlap)) if word]
        if overlap_words and index < len(words):
            index = max(start + 1, index - len(overlap_words))

    return chunks


def _build_overlap(text: str, max_tokens: int) -> str:
    if max_tokens <= 0:
        return ""

    selected: list[str] = []
    token_count = 0

    for sentence in reversed(_split_sentences(text)):
        next_count = token_count + estimate_token_count(sentence)
        if selected and next_count > max_tokens:
            break
        selected.insert(0, sentence)
        token_count = next_count

    return " ".join(selected)


def _join_chunk_content(left: str, right: str) -> str:
    if not left:
        return right.strip()
    if not right:
        return left.strip()
    return f"{left.strip()}\n\n{right.strip()}"


def estimate_token_count(text: str) -> int:
    trimmed = text.strip()
    if not trimmed:
        return 0
    return max(1, (len(trimmed) + 3) // 4)
