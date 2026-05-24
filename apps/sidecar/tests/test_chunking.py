from sidecar.chunking import chunk_elements
from sidecar.main import app
from sidecar.models import ChunkElement, ElementType
from fastapi.testclient import TestClient

client = TestClient(app)


def element(
    id: str,
    type: ElementType,
    content: str,
    position: int,
    *,
    level: int | None = None,
) -> ChunkElement:
    return ChunkElement(
        id=id,
        type=type,
        content=content,
        position=position,
        level=level,
    )


def test_heading_context_is_propagated_to_chunks():
    chunks = chunk_elements(
        source_id="src-1",
        elements=[
            element("e1", ElementType.heading, "Chapter 1", 0, level=1),
            element("e2", ElementType.heading, "Section A", 1, level=2),
            element("e3", ElementType.paragraph, "A useful paragraph.", 2),
        ],
    )

    assert len(chunks) == 1
    assert chunks[0].headingContext == "Chapter 1 > Section A"
    assert chunks[0].startElement == "e3"
    assert chunks[0].endElement == "e3"


def test_oversized_paragraph_splits_at_sentence_boundaries():
    chunks = chunk_elements(
        source_id="src-1",
        chunk_size=12,
        chunk_overlap=0,
        elements=[
            element(
                "e1",
                ElementType.paragraph,
                "First sentence is short. Second sentence is also short. Third sentence closes.",
                0,
            ),
        ],
    )

    assert len(chunks) > 1
    assert chunks[0].content.endswith(".")
    assert chunks[1].content.endswith(".")


def test_tables_are_not_split_even_when_large():
    table = "| A | B |\n| --- | --- |\n" + "\n".join(f"| {i} | {i} |" for i in range(40))

    chunks = chunk_elements(
        source_id="src-1",
        chunk_size=8,
        chunk_overlap=0,
        elements=[element("e1", ElementType.table, table, 0)],
    )

    assert len(chunks) == 1
    assert chunks[0].content == table


def test_positions_are_contiguous():
    chunks = chunk_elements(
        source_id="src-1",
        chunk_size=8,
        chunk_overlap=0,
        elements=[
            element("e1", ElementType.paragraph, "One sentence.", 0),
            element("e2", ElementType.paragraph, "Two sentence.", 1),
            element("e3", ElementType.paragraph, "Three sentence.", 2),
        ],
    )

    assert [chunk.position for chunk in chunks] == list(range(len(chunks)))


def test_chunk_endpoint_returns_chunks():
    response = client.post(
        "/chunk",
        json={
            "sourceId": "src-1",
            "chunkSize": 512,
            "chunkOverlap": 64,
            "elements": [
                {
                    "id": "e1",
                    "type": "heading",
                    "content": "Intro",
                    "position": 0,
                    "level": 1,
                },
                {
                    "id": "e2",
                    "type": "paragraph",
                    "content": "This is the first imported paragraph.",
                    "position": 1,
                },
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["sourceId"] == "src-1"
    assert payload["chunks"][0]["headingContext"] == "Intro"
    assert payload["chunks"][0]["startElement"] == "e2"
