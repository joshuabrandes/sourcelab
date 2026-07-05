from sidecar.extractors.utils import markdown_to_elements
from sidecar.models import ElementType


def test_markdown_ast_maps_supported_block_types():
    markdown = """# Title

A paragraph with *formatting*.

- first
- second

| A | B |
| --- | --- |
| 1 | 2 |

```python
print("hello")
```

![Diagram](diagram.png)
"""

    elements = markdown_to_elements(markdown, page=3, position_offset=4)

    assert [element.type for element in elements] == [
        ElementType.heading,
        ElementType.paragraph,
        ElementType.list,
        ElementType.table,
        ElementType.code,
        ElementType.image,
    ]
    assert [element.position for element in elements] == list(range(4, 10))
    assert all(element.page == 3 for element in elements)
    assert elements[0].level == 1
    assert elements[4].content == 'print("hello")'


def test_markdown_ast_preserves_empty_document_contract():
    elements = markdown_to_elements("", page=2, position_offset=7)

    assert len(elements) == 1
    assert elements[0].content == ""
    assert elements[0].page == 2
    assert elements[0].position == 7
