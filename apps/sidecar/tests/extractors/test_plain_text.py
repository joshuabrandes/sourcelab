import pytest

from sidecar.extractors.plain_text import _extract_elements, extract_plain_text_document
from sidecar.models import ContentType, ElementType


# ── _extract_elements (pure function) ────────────────────────────────────────

def test_empty_string_returns_single_empty_paragraph():
    elements = _extract_elements("")
    assert len(elements) == 1
    assert elements[0].type == ElementType.paragraph
    assert elements[0].content == ""
    assert elements[0].position == 0


def test_whitespace_only_returns_single_empty_paragraph():
    elements = _extract_elements("   \n\n   ")
    assert len(elements) == 1
    assert elements[0].type == ElementType.paragraph


def test_single_paragraph():
    elements = _extract_elements("Hello world")
    assert len(elements) == 1
    assert elements[0].type == ElementType.paragraph
    assert elements[0].content == "Hello world"


def test_two_paragraphs():
    elements = _extract_elements("First paragraph\n\nSecond paragraph")
    assert len(elements) == 2
    assert all(e.type == ElementType.paragraph for e in elements)
    assert elements[0].content == "First paragraph"
    assert elements[1].content == "Second paragraph"


def test_heading_level_1():
    elements = _extract_elements("# My Title")
    assert len(elements) == 1
    assert elements[0].type == ElementType.heading
    assert elements[0].content == "My Title"
    assert elements[0].level == 1


def test_heading_level_3():
    elements = _extract_elements("### Section")
    assert len(elements) == 1
    assert elements[0].type == ElementType.heading
    assert elements[0].level == 3


def test_heading_followed_by_paragraph():
    elements = _extract_elements("# Title\n\nSome text below")
    assert len(elements) == 2
    assert elements[0].type == ElementType.heading
    assert elements[1].type == ElementType.paragraph


def test_positions_are_contiguous():
    raw = "# Heading\n\nFirst para\n\nSecond para"
    elements = _extract_elements(raw)
    for i, element in enumerate(elements):
        assert element.position == i


def test_inline_hash_not_treated_as_heading():
    # A '#' that doesn't start the block is just a paragraph
    elements = _extract_elements("This has a # in the middle")
    assert elements[0].type == ElementType.paragraph


# ── extract_plain_text_document (file I/O) ────────────────────────────────────

def test_extract_txt_file(tmp_path):
    f = tmp_path / "hello.txt"
    f.write_text("Hello world", encoding="utf-8")

    doc = extract_plain_text_document("src-1", str(f))

    assert doc.sourceId == "src-1"
    assert doc.title == "hello"
    assert doc.contentType == ContentType.txt
    assert len(doc.elements) == 1
    assert doc.elements[0].content == "Hello world"


def test_extract_md_file(tmp_path):
    f = tmp_path / "notes.md"
    f.write_text("# Title\n\nSome content", encoding="utf-8")

    doc = extract_plain_text_document("src-2", str(f))

    assert doc.contentType == ContentType.md
    assert doc.elements[0].type == ElementType.heading
    assert doc.elements[1].type == ElementType.paragraph


def test_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        extract_plain_text_document("src-x", str(tmp_path / "nonexistent.txt"))


def test_unsupported_extension_raises(tmp_path):
    f = tmp_path / "file.xyz"
    f.write_text("content", encoding="utf-8")

    with pytest.raises(ValueError, match="Unsupported file type"):
        extract_plain_text_document("src-x", str(f))


def test_metadata_has_page_count(tmp_path):
    f = tmp_path / "doc.txt"
    f.write_text("Some text", encoding="utf-8")

    doc = extract_plain_text_document("src-3", str(f))
    assert doc.metadata.pageCount == 1
    assert doc.metadata.extractedAt is not None