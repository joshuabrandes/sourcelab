from marker.renderers.json import JSONBlockOutput, JSONOutput

from sidecar.extractors.pdf import _first_language, _marker_output_to_elements
from sidecar.models import ElementType


def block(block_type: str, html: str, block_id: str) -> JSONBlockOutput:
    return JSONBlockOutput(
        id=block_id,
        block_type=block_type,
        html=html,
        polygon=[[0, 0], [100, 0], [100, 20], [0, 20]],
        bbox=[0, 0, 100, 20],
    )


def test_marker_blocks_preserve_type_page_and_geometry():
    page_one = block("Page", "", "/page/0")
    page_one.children = [
        block("PageHeader", "<p>Repeated header</p>", "/page/0/PageHeader/0"),
        block("SectionHeader", "<h2>Introduction</h2>", "/page/0/SectionHeader/1"),
        block("Text", "<p>Useful content.</p>", "/page/0/Text/2"),
        block(
            "Table",
            "<table><tr><th>A</th><th>B</th></tr><tr><td>1</td><td>2</td></tr></table>",
            "/page/0/Table/3",
        ),
    ]
    page_two = block("Page", "", "/page/1")
    page_two.children = [block("Code", "<pre>x = 1</pre>", "/page/1/Code/0")]
    output = JSONOutput(children=[page_one, page_two], metadata={"languages": ["de"]})

    elements = _marker_output_to_elements(output)

    assert [element.type for element in elements] == [
        ElementType.heading,
        ElementType.paragraph,
        ElementType.table,
        ElementType.code,
    ]
    assert [element.page for element in elements] == [1, 1, 1, 2]
    assert [element.position for element in elements] == [0, 1, 2, 3]
    assert elements[0].level == 2
    assert elements[1].metadata["bbox"] == [0.0, 0.0, 100.0, 20.0]
    assert "| A | B |" in elements[2].content
    assert _first_language(output.metadata) == "de"
