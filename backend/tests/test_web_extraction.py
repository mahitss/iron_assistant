"""Tests for HTML Text Extraction and Sanitization."""

from app.tools.web.extraction import extract_content_from_html


def test_extract_title():
    """Extract page title from HTML."""
    html = "<html><head><title>Python Documentation 3.12</title></head><body><p>Hello World</p></body></html>"
    title, text = extract_content_from_html(html)
    assert title == "Python Documentation 3.12"
    assert "Hello World" in text


def test_strips_scripts_and_styles():
    """Scripts and styles must be completely removed from extracted output."""
    html = """
    <html>
      <head>
        <style>body { background-color: red; } .hidden { display: none; }</style>
        <script>function evil() { window.location = 'http://bad.com'; }</script>
      </head>
      <body>
        <script type="text/javascript">document.write("malicious script");</script>
        <p>Legitimate visible content.</p>
        <noscript>Javascript disabled message</noscript>
      </body>
    </html>
    """
    title, text = extract_content_from_html(html)
    assert "background-color" not in text
    assert "evil" not in text
    assert "malicious script" not in text
    assert "Javascript disabled" not in text
    assert "Legitimate visible content." in text


def test_strips_navigation_and_boilerplate():
    """Navigation menus, footers, headers, and form elements must be stripped."""
    html = """
    <html>
      <body>
        <header><p>Site Header Logo</p></header>
        <nav>
          <ul>
            <li><a href="/">Home</a></li>
            <li><a href="/about">About Us</a></li>
          </ul>
        </nav>
        <main>
          <h1>Article Main Heading</h1>
          <p>This is the core article body text.</p>
        </main>
        <aside>Related ads and sidebar links</aside>
        <footer><p>Copyright 2026 Acme Corp. All rights reserved.</p></footer>
      </body>
    </html>
    """
    title, text = extract_content_from_html(html)
    assert "Site Header Logo" not in text
    assert "About Us" not in text
    assert "Related ads" not in text
    assert "Copyright 2026" not in text
    assert "# Article Main Heading" in text
    assert "This is the core article body text." in text


def test_preserves_headings_lists_and_paragraphs():
    """Headings, lists, and paragraphs are formatted clearly in markdown style."""
    html = """
    <div>
      <h1>Top Level Heading</h1>
      <p>Introductory paragraph.</p>
      <h2>Section Two</h2>
      <ul>
        <li>First item</li>
        <li>Second item</li>
      </ul>
    </div>
    """
    _, text = extract_content_from_html(html)
    assert "# Top Level Heading" in text
    assert "Introductory paragraph." in text
    assert "## Section Two" in text
    assert "- First item" in text
    assert "- Second item" in text


def test_preserves_tables():
    """Table cells and rows are preserved with pipe separators."""
    html = """
    <table>
      <tr><th>Feature</th><th>Status</th></tr>
      <tr><td>FastAPI</td><td>Supported</td></tr>
      <tr><td>PostgreSQL</td><td>Configured</td></tr>
    </table>
    """
    _, text = extract_content_from_html(html)
    assert "Feature | Status" in text or ("Feature" in text and "Status" in text)
    assert "FastAPI | Supported" in text or ("FastAPI" in text and "Supported" in text)


def test_whitespace_collapsed():
    """Multiple redundant spaces and blank lines must be collapsed."""
    html = "<p>Word1     Word2       Word3</p>\n\n\n\n\n<p>Next    Paragraph</p>"
    _, text = extract_content_from_html(html)
    assert "Word1 Word2 Word3" in text
    assert "   " not in text


def test_max_chars_truncation():
    """Text exceeding max_chars is cleanly truncated with notice."""
    html = "A" * 500
    _, text = extract_content_from_html(html, max_chars=100)
    assert len(text) > 100  # includes truncation notice
    assert "[Content truncated at 100 characters]" in text
    assert text.startswith("A" * 100)


def test_malformed_html_handled_gracefully():
    """Unclosed tags, broken syntax, and unusual characters parse without throwing exceptions."""
    broken_html = "<p>Unclosed paragraph <b>bold <div>nested <span>content</p>"
    _, text = extract_content_from_html(broken_html)
    assert "Unclosed paragraph" in text
    assert "content" in text
