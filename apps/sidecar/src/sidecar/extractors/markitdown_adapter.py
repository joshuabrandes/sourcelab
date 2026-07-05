from pathlib import Path
from typing import Any

_converter: Any | None = None


def convert_to_markdown(path: Path) -> tuple[str, str | None]:
    result = _get_converter().convert(str(path))
    markdown = getattr(result, "markdown", None) or getattr(result, "text_content", None)
    if not isinstance(markdown, str):
        raise TypeError("MarkItDown returned no Markdown content")
    title = getattr(result, "title", None)
    return markdown, title if isinstance(title, str) and title.strip() else None


def _get_converter() -> Any:
    global _converter
    if _converter is None:
        from markitdown import MarkItDown

        _converter = MarkItDown(enable_plugins=False)
    return _converter
