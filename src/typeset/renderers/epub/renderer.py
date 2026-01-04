"""EPUB renderer using ebooklib."""

import html
import uuid
from pathlib import Path

from ebooklib import epub

from typeset.config.models import EpubConfig
from typeset.ir.document import Chapter, Document
from typeset.ir.nodes import ImageNode, Node, NodeType
from typeset.renderers.base import BaseRenderer


class EpubRenderer(BaseRenderer):
    """Render IR Document to EPUB format."""

    def __init__(self, config: EpubConfig | None = None):
        self.config = config or EpubConfig()
        self.image_items: dict[str, epub.EpubImage] = {}

    def get_extension(self) -> str:
        return ".epub"

    def render(self, document: Document, output_path: str | Path) -> None:
        """Render document to EPUB file."""
        output_path = Path(output_path)
        book = epub.EpubBook()

        # Set metadata
        self._set_metadata(book, document)

        # Add images first (so chapters can reference them)
        self._add_images(book, document)

        # Create chapters
        chapters = []
        for i, chapter in enumerate(document.chapters):
            epub_chapter = self._create_chapter(chapter, i)
            book.add_item(epub_chapter)
            chapters.append(epub_chapter)

        # Add default CSS
        css = self._generate_css()
        nav_css = epub.EpubItem(
            uid="style_default",
            file_name="style/default.css",
            media_type="text/css",
            content=css.encode("utf-8"),
        )
        book.add_item(nav_css)

        # Apply CSS to chapters
        for chapter in chapters:
            chapter.add_item(nav_css)

        # Create TOC
        book.toc = self._create_toc(chapters, document)

        # Create spine (reading order)
        book.spine = ["nav"] + chapters

        # Add navigation files
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())

        # Write to file
        epub.write_epub(str(output_path), book, {})

    def _set_metadata(self, book: epub.EpubBook, document: Document) -> None:
        """Set EPUB metadata."""
        meta = document.metadata

        # Required metadata
        identifier = meta.isbn_epub or meta.isbn or f"urn:uuid:{uuid.uuid4()}"
        book.set_identifier(identifier)
        book.set_title(meta.title)
        book.set_language(meta.language or self.config.language)

        # Authors
        for author in meta.authors:
            book.add_author(author)

        # Optional metadata
        if meta.publisher:
            book.add_metadata("DC", "publisher", meta.publisher)
        if meta.description:
            book.add_metadata("DC", "description", meta.description)
        if meta.publication_date:
            book.add_metadata("DC", "date", meta.publication_date)

        # Cover image
        if meta.cover_image:
            book.set_cover("cover.jpg", meta.cover_image)
        elif self.config.cover_image and self.config.cover_image.exists():
            cover_data = self.config.cover_image.read_bytes()
            book.set_cover("cover.jpg", cover_data)

    def _add_images(self, book: epub.EpubBook, document: Document) -> None:
        """Add images to EPUB."""
        image_counter = 0
        for chapter in document.chapters:
            self._collect_images(chapter.content, book, image_counter)

    def _collect_images(
        self, nodes: list[Node], book: epub.EpubBook, counter: int
    ) -> int:
        """Recursively collect and add images."""
        for node in nodes:
            if isinstance(node, ImageNode) and node.src:
                counter += 1
                ext = node.mime_type.split("/")[-1]
                filename = f"images/image_{counter}.{ext}"

                epub_image = epub.EpubImage()
                epub_image.file_name = filename
                epub_image.media_type = node.mime_type
                epub_image.content = node.src
                book.add_item(epub_image)

                # Store reference for chapter rendering
                self.image_items[id(node)] = epub_image

            counter = self._collect_images(node.children, book, counter)

        return counter

    def _create_chapter(self, chapter: Chapter, index: int) -> epub.EpubHtml:
        """Create EPUB chapter from IR Chapter."""
        content_html = self._render_nodes(chapter.content)

        # Build chapter HTML
        chapter_html = f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head>
    <title>{html.escape(chapter.title)}</title>
    <link rel="stylesheet" type="text/css" href="style/default.css"/>
</head>
<body>
    <section epub:type="chapter" id="{chapter.id}">
        {f'<h1>{html.escape(chapter.title)}</h1>' if chapter.title else ''}
        {content_html}
    </section>
</body>
</html>"""

        epub_chapter = epub.EpubHtml(
            title=chapter.title or f"Chapter {index + 1}",
            file_name=f"chap_{index:03d}.xhtml",
            lang=self.config.language,
        )
        epub_chapter.content = chapter_html.encode("utf-8")

        return epub_chapter

    def _render_nodes(self, nodes: list[Node]) -> str:
        """Render IR nodes to HTML."""
        return "\n".join(self._node_to_html(node) for node in nodes)

    def _node_to_html(self, node: Node) -> str:
        """Convert single IR node to HTML."""
        if isinstance(node, ImageNode):
            if id(node) in self.image_items:
                src = self.image_items[id(node)].file_name
            else:
                src = node.filename
            alt = html.escape(node.alt_text or "")
            caption = ""
            if node.caption:
                caption = f"<figcaption>{html.escape(node.caption)}</figcaption>"
            return f'<figure><img src="{src}" alt="{alt}"/>{caption}</figure>'

        match node.node_type:
            case NodeType.PARAGRAPH:
                inner = self._render_children(node)
                return f"<p>{inner}</p>"

            case NodeType.HEADING:
                from typeset.ir.nodes import HeadingNode

                level = node.level if isinstance(node, HeadingNode) else 2
                inner = self._render_children(node)
                return f"<h{level}>{inner}</h{level}>"

            case NodeType.STRONG:
                inner = self._render_children(node)
                return f"<strong>{inner}</strong>"

            case NodeType.EMPHASIS:
                inner = self._render_children(node)
                return f"<em>{inner}</em>"

            case NodeType.STRIKETHROUGH:
                inner = self._render_children(node)
                return f"<del>{inner}</del>"

            case NodeType.SUPERSCRIPT:
                inner = self._render_children(node)
                return f"<sup>{inner}</sup>"

            case NodeType.SUBSCRIPT:
                inner = self._render_children(node)
                return f"<sub>{inner}</sub>"

            case NodeType.TEXT:
                from typeset.ir.nodes import TextNode

                if isinstance(node, TextNode):
                    return html.escape(node.text)
                return ""

            case NodeType.LINK:
                from typeset.ir.nodes import LinkNode

                if isinstance(node, LinkNode):
                    inner = self._render_children(node)
                    return f'<a href="{html.escape(node.url)}">{inner}</a>'
                return self._render_children(node)

            case NodeType.BLOCKQUOTE:
                inner = self._render_children(node)
                return f"<blockquote>{inner}</blockquote>"

            case NodeType.LIST:
                from typeset.ir.nodes import ListNode

                tag = "ol" if isinstance(node, ListNode) and node.ordered else "ul"
                inner = self._render_children(node)
                return f"<{tag}>{inner}</{tag}>"

            case NodeType.LIST_ITEM:
                inner = self._render_children(node)
                return f"<li>{inner}</li>"

            case NodeType.TABLE:
                inner = self._render_children(node)
                return f"<table>{inner}</table>"

            case NodeType.TABLE_ROW:
                inner = self._render_children(node)
                return f"<tr>{inner}</tr>"

            case NodeType.TABLE_CELL:
                inner = self._render_children(node)
                return f"<td>{inner}</td>"

            case NodeType.CODE_BLOCK:
                inner = self._render_children(node)
                return f"<pre><code>{inner}</code></pre>"

            case NodeType.CODE:
                inner = self._render_children(node)
                return f"<code>{inner}</code>"

            case NodeType.HORIZONTAL_RULE:
                return "<hr/>"

            case NodeType.PAGE_BREAK:
                return '<div class="page-break"></div>'

            case _:
                # Default: just render children
                return self._render_children(node)

    def _render_children(self, node: Node) -> str:
        """Render all children of a node."""
        return "".join(self._node_to_html(child) for child in node.children)

    def _create_toc(
        self, chapters: list[epub.EpubHtml], document: Document
    ) -> list[epub.Link | tuple]:
        """Create table of contents."""
        toc = []
        for epub_chapter, ir_chapter in zip(chapters, document.chapters):
            if ir_chapter.title:
                toc.append(epub.Link(epub_chapter.file_name, ir_chapter.title, ir_chapter.id))
        return toc

    def _generate_css(self) -> str:
        """Generate default CSS for EPUB."""
        return """/* Default EPUB Stylesheet */

body {
    font-family: Georgia, "Times New Roman", serif;
    font-size: 1em;
    line-height: 1.6;
    margin: 1em;
    text-align: justify;
}

h1, h2, h3, h4, h5, h6 {
    font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
    font-weight: bold;
    line-height: 1.2;
    margin-top: 1.5em;
    margin-bottom: 0.5em;
    text-align: left;
}

h1 {
    font-size: 2em;
    margin-top: 2em;
    page-break-before: always;
}

h2 { font-size: 1.5em; }
h3 { font-size: 1.25em; }
h4 { font-size: 1.1em; }

p {
    margin: 0;
    text-indent: 1.5em;
}

p:first-of-type,
h1 + p, h2 + p, h3 + p, h4 + p,
blockquote + p,
figure + p {
    text-indent: 0;
}

blockquote {
    margin: 1em 2em;
    font-style: italic;
    border-left: 3px solid #ccc;
    padding-left: 1em;
}

figure {
    margin: 1em 0;
    text-align: center;
}

figure img {
    max-width: 100%;
    height: auto;
}

figcaption {
    font-size: 0.9em;
    font-style: italic;
    margin-top: 0.5em;
    color: #666;
}

table {
    width: 100%;
    border-collapse: collapse;
    margin: 1em 0;
}

th, td {
    border: 1px solid #ccc;
    padding: 0.5em;
    text-align: left;
}

th {
    background-color: #f5f5f5;
    font-weight: bold;
}

a {
    color: #0066cc;
    text-decoration: none;
}

a:hover {
    text-decoration: underline;
}

.page-break {
    page-break-after: always;
}

sup, sub {
    font-size: 0.75em;
    line-height: 0;
}

sup { vertical-align: super; }
sub { vertical-align: sub; }

del {
    text-decoration: line-through;
}

code {
    font-family: "Courier New", Courier, monospace;
    font-size: 0.9em;
    background-color: #f5f5f5;
    padding: 0.1em 0.3em;
    border-radius: 3px;
}

pre {
    font-family: "Courier New", Courier, monospace;
    font-size: 0.85em;
    background-color: #f5f5f5;
    padding: 1em;
    overflow-x: auto;
    white-space: pre-wrap;
    border-radius: 3px;
}
"""
