import httpx

from sidecar.extractors.html_url import extract_html_document, extract_url_document
from sidecar.models import ContentType, ElementType

HTML = """
<html>
  <head>
    <title>Useful Article</title>
    <meta name="author" content="Linus Torvalds">
  </head>
  <body>
    <nav>Navigation noise</nav>
    <main>
      <h1>Article Heading</h1>
      <p>Important content.</p>
      <table><tr><th>A</th><th>B</th></tr><tr><td>1</td><td>2</td></tr></table>
    </main>
  </body>
</html>
"""


def test_extract_html_document_uses_main_content_and_metadata(tmp_path):
    path = tmp_path / "article.html"
    path.write_text(HTML, encoding="utf-8")

    extracted = extract_html_document("source-1", str(path))

    assert extracted.contentType == ContentType.html
    assert extracted.title == "Useful Article"
    assert extracted.metadata.author == "Linus Torvalds"
    assert any(element.type == ElementType.heading for element in extracted.elements)
    assert any("Important content" in element.content for element in extracted.elements)


def test_extract_url_reports_http_status(mocker):
    request = httpx.Request("GET", "https://example.com/missing")
    response = httpx.Response(404, request=request)
    client = mocker.MagicMock()
    client.__enter__.return_value = client
    client.__exit__.return_value = False
    client.get.return_value = response
    mocker.patch("sidecar.extractors.html_url.httpx.Client", return_value=client)

    try:
        extract_url_document("source-1", "https://example.com/missing")
    except ValueError as exc:
        assert "HTTP 404" in str(exc)
    else:
        raise AssertionError("Expected URL extraction to fail")
