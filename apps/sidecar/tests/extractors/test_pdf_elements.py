"""
Tests for the pure _extract_elements function in the PDF extractor.
The full extract_pdf_document function is not tested here because it requires
heavy ML models (marker) — that belongs in an integration test.
"""

from sidecar.extractors.pdf import _extract_elements
from sidecar.models import ElementType


# ── edge cases ────────────────────────────────────────────────────────────────

def test_empty_string_returns_single_empty_paragraph():
    elements = _extract_elements("")
    assert len(elements) == 1
    assert elements[0].type == ElementType.paragraph
    assert elements[0].content == ""


def test_whitespace_only_returns_single_empty_paragraph():
    elements = _extract_elements("  \n\n  ")
    assert len(elements) == 1
    assert elements[0].type == ElementType.paragraph


# ── headings ─────────────────────────────────────────────────────────────────

def test_heading_level_1():
    elements = _extract_elements("# Introduction")
    assert len(elements) == 1
    assert elements[0].type == ElementType.heading
    assert elements[0].content == "Introduction"
    assert elements[0].level == 1


def test_heading_level_6_capped():
    elements = _extract_elements("###### Deep")
    assert elements[0].type == ElementType.heading
    assert elements[0].level == 6


def test_heading_level_clamped_at_1():
    # Only one '#' — level should be 1
    elements = _extract_elements("# Top")
    assert elements[0].level == 1


# ── code blocks ───────────────────────────────────────────────────────────────

def test_fenced_code_block():
    md = "```python\nprint('hello')\n```"
    elements = _extract_elements(md)
    assert len(elements) == 1
    assert elements[0].type == ElementType.code
    assert "print('hello')" in elements[0].content


def test_code_block_without_language_tag():
    md = "```\nx = 1\n```"
    elements = _extract_elements(md)
    assert elements[0].type == ElementType.code
    assert "x = 1" in elements[0].content


def test_code_block_not_split_on_blank_lines():
    md = "```\nline1\n\nline2\n```"
    elements = _extract_elements(md)
    assert len(elements) == 1
    assert elements[0].type == ElementType.code


# ── images ────────────────────────────────────────────────────────────────────

def test_markdown_image():
    elements = _extract_elements("![alt text](https://example.com/img.png)")
    assert len(elements) == 1
    assert elements[0].type == ElementType.image


# ── tables ────────────────────────────────────────────────────────────────────

def test_pipe_table():
    table = "| Col A | Col B |\n| ----- | ----- |\n| a     | b     |"
    elements = _extract_elements(table)
    assert len(elements) == 1
    assert elements[0].type == ElementType.table


# ── lists ─────────────────────────────────────────────────────────────────────

def test_unordered_list_dash():
    elements = _extract_elements("- item one\n- item two")
    assert len(elements) == 1
    assert elements[0].type == ElementType.list


def test_unordered_list_asterisk():
    elements = _extract_elements("* item one\n* item two")
    assert elements[0].type == ElementType.list


def test_ordered_list():
    elements = _extract_elements("1. first\n2. second")
    assert elements[0].type == ElementType.list


# ── positions ─────────────────────────────────────────────────────────────────

def test_positions_are_contiguous():
    md = "# Heading\n\n```\ncode\n```\n\n| a | b |\n| - | - |\n| 1 | 2 |"
    elements = _extract_elements(md)
    for i, el in enumerate(elements):
        assert el.position == i


# ── mixed content ─────────────────────────────────────────────────────────────

def test_mixed_content_types():
    md = "\n".join([
        "# Title",
        "",
        "A paragraph here.",
        "",
        "```python",
        "x = 42",
        "```",
        "",
        "- bullet",
    ])
    elements = _extract_elements(md)
    types = [e.type for e in elements]
    assert ElementType.heading in types
    assert ElementType.code in types
    assert ElementType.list in types