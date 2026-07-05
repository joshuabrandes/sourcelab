from collections.abc import Iterable
from datetime import UTC, datetime

from markdown_it import MarkdownIt
from markdown_it.token import Token

from sidecar.models import DocumentElement, ElementType

_MARKDOWN = MarkdownIt("commonmark").enable("table")


def markdown_to_elements(
    markdown: str,
    *,
    page: int | None = None,
    position_offset: int = 0,
) -> list[DocumentElement]:
    stripped = markdown.strip()
    if not stripped:
        return [
            DocumentElement(
                type=ElementType.paragraph,
                content="",
                page=page,
                position=position_offset,
            )
        ]

    source_lines = markdown.splitlines()
    tokens = _MARKDOWN.parse(markdown)
    elements: list[DocumentElement] = []

    for index, token in enumerate(tokens):
        if token.level != 0 or token.nesting < 0:
            continue

        element_type = _element_type(token, tokens, index)
        if element_type is None:
            continue

        content = _element_content(token, tokens, index, source_lines, element_type)
        level = _heading_level(token) if element_type == ElementType.heading else None
        elements.append(
            DocumentElement(
                type=element_type,
                content=content,
                page=page,
                level=level,
                position=position_offset + len(elements),
            )
        )

    if elements:
        return elements

    return [
        DocumentElement(
            type=ElementType.paragraph,
            content=stripped,
            page=page,
            position=position_offset,
        )
    ]


def utc_timestamp() -> str:
    return datetime.now(UTC).isoformat()


def rows_to_markdown_table(rows: Iterable[Iterable[str]]) -> str:
    formatted_rows: list[str] = []
    for row_index, row in enumerate(rows):
        cells = [_escape_table_cell(cell) for cell in row]
        formatted_rows.append("| " + " | ".join(cells) + " |")
        if row_index == 0:
            formatted_rows.append("| " + " | ".join("---" for _ in cells) + " |")
    return "\n".join(formatted_rows)


def _element_type(
    token: Token,
    tokens: list[Token],
    index: int,
) -> ElementType | None:
    if token.type == "heading_open":
        return ElementType.heading
    if token.type in {"fence", "code_block"}:
        return ElementType.code
    if token.type == "table_open":
        return ElementType.table
    if token.type in {"bullet_list_open", "ordered_list_open"}:
        return ElementType.list
    if token.type == "paragraph_open":
        inline = _following_inline(tokens, index)
        if inline is not None and inline.children and all(
            child.type in {"image", "softbreak", "hardbreak"} for child in inline.children
        ):
            return ElementType.image
        return ElementType.paragraph
    if token.type in {"html_block", "blockquote_open"}:
        return ElementType.paragraph
    return None


def _element_content(
    token: Token,
    tokens: list[Token],
    index: int,
    source_lines: list[str],
    element_type: ElementType,
) -> str:
    if token.type in {"fence", "code_block"}:
        return token.content.rstrip("\n")
    if element_type == ElementType.heading:
        inline = _following_inline(tokens, index)
        return inline.content.strip() if inline is not None else _source_slice(token, source_lines)
    return _source_slice(token, source_lines)


def _source_slice(token: Token, source_lines: list[str]) -> str:
    if token.map is None:
        return token.content.strip()
    start, end = token.map
    return "\n".join(source_lines[start:end]).strip()


def _following_inline(tokens: list[Token], index: int) -> Token | None:
    if index + 1 < len(tokens) and tokens[index + 1].type == "inline":
        return tokens[index + 1]
    return None


def _heading_level(token: Token) -> int:
    if len(token.tag) == 2 and token.tag[0] == "h" and token.tag[1].isdigit():
        return max(1, min(int(token.tag[1]), 6))
    return 1


def _escape_table_cell(value: str) -> str:
    return value.strip().replace("\n", " ").replace("|", "\\|")
