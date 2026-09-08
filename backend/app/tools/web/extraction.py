"""HTML text extraction and sanitization for Kairo Web Research."""

import re
from html.parser import HTMLParser


class HTMLTextExtractor(HTMLParser):
    """Parses HTML into sanitized, structured plain text while stripping scripts, styles, and navigation boilerplate."""

    # Tags whose entire subtree (content and tags) must be dropped
    DROPPED_TAGS = frozenset(
        {
            "script",
            "style",
            "noscript",
            "svg",
            "nav",
            "header",
            "footer",
            "aside",
            "template",
            "iframe",
            "button",
            "input",
            "select",
            "textarea",
        }
    )

    # Tags that introduce block-level line breaks
    BLOCK_TAGS = frozenset(
        {
            "p",
            "div",
            "section",
            "article",
            "main",
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
            "li",
            "tr",
            "blockquote",
            "pre",
            "hr",
            "br",
        }
    )

    def __init__(self, max_chars: int = 30000) -> None:
        super().__init__(convert_charrefs=True)
        self.max_chars = max_chars
        self._pieces: list[str] = []
        self._ignore_stack: list[str] = []
        self._in_title = False
        self.title = ""
        self._char_count = 0
        self.truncated = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag_lower = tag.lower()

        if tag_lower == "title":
            self._in_title = True
            return

        if tag_lower in self.DROPPED_TAGS:
            self._ignore_stack.append(tag_lower)
            return

        if self._ignore_stack:
            return

        if tag_lower in self.BLOCK_TAGS:
            if tag_lower in {"h1", "h2", "h3", "h4", "h5", "h6"}:
                level = int(tag_lower[1])
                self._add_text("\n\n" + "#" * level + " ")
            elif tag_lower == "li":
                self._add_text("\n- ")
            elif tag_lower == "tr":
                self._add_text("\n")
            elif tag_lower in {"td", "th"}:
                self._add_text(" | ")
            elif tag_lower == "br":
                self._add_text("\n")
            else:
                self._add_text("\n\n")

    def handle_endtag(self, tag: str) -> None:
        tag_lower = tag.lower()

        if tag_lower == "title":
            self._in_title = False
            return

        if self._ignore_stack and self._ignore_stack[-1] == tag_lower:
            self._ignore_stack.pop()
            return

        if self._ignore_stack:
            return

        if tag_lower in self.BLOCK_TAGS and tag_lower not in {"br", "td", "th"}:
            self._add_text("\n")

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title += data
            return

        if self._ignore_stack or self.truncated:
            return

        self._add_text(data)

    def _add_text(self, text: str) -> None:
        if self.truncated:
            return

        new_count = self._char_count + len(text)
        if new_count > self.max_chars:
            allowed = max(0, self.max_chars - self._char_count)
            self._pieces.append(text[:allowed])
            self._char_count += allowed
            self.truncated = True
        else:
            self._pieces.append(text)
            self._char_count = new_count

    def get_extracted_text(self) -> str:
        """Post-process accumulated pieces by normalizing whitespace and trimming."""
        raw_text = "".join(self._pieces)

        # Normalize line-level whitespace
        lines = [re.sub(r"[ \t]+", " ", line).strip() for line in raw_text.splitlines()]

        # Collapse multiple empty lines into at most two
        cleaned_lines: list[str] = []
        blank_count = 0
        for line in lines:
            if not line:
                blank_count += 1
                if blank_count <= 2:
                    cleaned_lines.append("")
            else:
                blank_count = 0
                cleaned_lines.append(line)

        result = "\n".join(cleaned_lines).strip()

        if self.truncated:
            result += f"\n\n[Content truncated at {self.max_chars} characters]"

        return result


def extract_content_from_html(
    html: str,
    max_chars: int = 30000,
) -> tuple[str, str]:
    """Extract clean title and content from raw HTML string.

    Returns:
        tuple[title, extracted_text]
    """
    if not html or not isinstance(html, str):
        return "", ""

    parser = HTMLTextExtractor(max_chars=max_chars)
    try:
        parser.feed(html)
        parser.close()
    except Exception:
        # html.parser is resilient, but if deeply broken HTML fails, do best-effort text regex
        pass

    title = parser.title.strip()
    text = parser.get_extracted_text()
    return title, text
