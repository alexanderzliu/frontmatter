"""PDF renderer using WeasyPrint."""

import base64
import html
from pathlib import Path

from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration

from typeset.config.models import PdfConfig
from typeset.ir.document import Document, Chapter
from typeset.ir.nodes import ImageNode, Node, NodeType
from typeset.renderers.base import BaseRenderer


class PdfRenderer(BaseRenderer):
    """Render IR Document to print-ready PDF."""

    def __init__(self, config: PdfConfig | None = None):
        self.config = config or PdfConfig()
        self.font_config = FontConfiguration()

    def get_extension(self) -> str:
        return ".pdf"

    def render(self, document: Document, output_path: str | Path) -> None:
        """Render document to PDF file."""
        output_path = Path(output_path)

        # Generate HTML from IR
        html_content = self._generate_html(document)

        # Generate print CSS
        css_content = self._generate_print_css()

        # Render PDF with WeasyPrint
        html_doc = HTML(string=html_content, base_url=str(output_path.parent))
        css = CSS(string=css_content, font_config=self.font_config)

        html_doc.write_pdf(
            str(output_path),
            stylesheets=[css],
            font_config=self.font_config,
        )

    def _generate_html(self, document: Document) -> str:
        """Generate HTML document from IR."""
        meta = document.metadata

        # Build chapters HTML
        chapters_html = []
        for i, chapter in enumerate(document.chapters):
            chapter_html = self._render_chapter(chapter, i)
            chapters_html.append(chapter_html)

        # Build title page
        title_page = ""
        if self.config.include_title_page:
            title_page = self._generate_title_page(meta)

        # Build copyright page
        copyright_page = ""
        if self.config.include_copyright_page and meta.copyright:
            copyright_page = f"""
            <section class="copyright-page">
                <p>{html.escape(meta.copyright)}</p>
                {f'<p>ISBN: {html.escape(meta.isbn_print)}</p>' if meta.isbn_print else ''}
            </section>
            """

        # Build TOC
        toc_html = ""
        if self.config.include_toc:
            toc_html = self._generate_toc(document)

        return f"""<!DOCTYPE html>
<html lang="{meta.language}">
<head>
    <meta charset="utf-8">
    <title>{html.escape(meta.title)}</title>
</head>
<body>
    <div class="book-title" style="string-set: book-title '{html.escape(meta.title)}'"></div>
    {title_page}
    {copyright_page}
    {toc_html}
    {"".join(chapters_html)}
</body>
</html>"""

    def _generate_title_page(self, meta) -> str:
        """Generate title page HTML."""
        authors = ", ".join(meta.authors) if meta.authors else ""
        subtitle = f"<p class='subtitle'>{html.escape(meta.subtitle)}</p>" if meta.subtitle else ""

        return f"""
        <section class="title-page">
            <h1 class="book-title">{html.escape(meta.title)}</h1>
            {subtitle}
            <p class="author">{html.escape(authors)}</p>
            {f'<p class="publisher">{html.escape(meta.publisher)}</p>' if meta.publisher else ''}
        </section>
        """

    def _generate_toc(self, document: Document) -> str:
        """Generate table of contents HTML."""
        entries = []
        for chapter in document.chapters:
            if chapter.title:
                entries.append(
                    f'<li><a href="#{chapter.id}">{html.escape(chapter.title)}</a></li>'
                )

        if not entries:
            return ""

        return f"""
        <section class="toc">
            <h2>Contents</h2>
            <nav>
                <ol>
                    {"".join(entries)}
                </ol>
            </nav>
        </section>
        """

    def _render_chapter(self, chapter: Chapter, index: int) -> str:
        """Render a chapter to HTML."""
        content = self._render_nodes(chapter.content)

        title_html = ""
        if chapter.title:
            title_html = f'<h1 class="chapter-title" style="string-set: chapter-title \'{html.escape(chapter.title)}\'">{html.escape(chapter.title)}</h1>'

        return f"""
        <section class="chapter" id="{chapter.id}">
            {title_html}
            {content}
        </section>
        """

    def _render_nodes(self, nodes: list[Node]) -> str:
        """Render IR nodes to HTML."""
        return "\n".join(self._node_to_html(node) for node in nodes)

    def _node_to_html(self, node: Node) -> str:
        """Convert single IR node to HTML."""
        if isinstance(node, ImageNode):
            return self._render_image(node)

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
                return self._render_children(node)

    def _render_children(self, node: Node) -> str:
        """Render all children of a node."""
        return "".join(self._node_to_html(child) for child in node.children)

    def _render_image(self, node: ImageNode) -> str:
        """Render an image node."""
        if node.src:
            # Embed image as data URI
            b64_data = base64.b64encode(node.src).decode("utf-8")
            src = f"data:{node.mime_type};base64,{b64_data}"
        else:
            src = node.filename

        alt = html.escape(node.alt_text or "")

        if node.caption:
            caption = f"<figcaption>{html.escape(node.caption)}</figcaption>"
            return f'<figure><img src="{src}" alt="{alt}"/>{caption}</figure>'

        return f'<figure><img src="{src}" alt="{alt}"/></figure>'

    def _generate_print_css(self) -> str:
        """Generate print-specific CSS with @page rules."""
        cfg = self.config
        margins = cfg.margins

        # Build @page rules
        bleed_rules = ""
        if cfg.bleed:
            bleed_rules = f"""
    bleed: {cfg.bleed};
    marks: crop cross;"""

        page_number_rules = ""
        if cfg.show_page_numbers:
            if cfg.page_number_position == "bottom-center":
                page_number_rules = """
    @bottom-center {
        content: counter(page);
        font-family: sans-serif;
        font-size: 10pt;
    }"""
            else:  # bottom-outside
                page_number_rules = ""

        return f"""/* Print CSS for book layout */

@page {{
    size: {cfg.page_size};
    margin: {margins.top} {margins.outside} {margins.bottom} {margins.inside};
    {bleed_rules}
    {page_number_rules}
}}

@page :left {{
    margin-left: {margins.outside};
    margin-right: {margins.inside};

    @bottom-left {{
        content: counter(page);
        font-family: sans-serif;
        font-size: 10pt;
    }}

    @top-left {{
        content: string(chapter-title);
        font-family: sans-serif;
        font-size: 9pt;
        font-style: italic;
    }}
}}

@page :right {{
    margin-left: {margins.inside};
    margin-right: {margins.outside};

    @bottom-right {{
        content: counter(page);
        font-family: sans-serif;
        font-size: 10pt;
    }}

    @top-right {{
        content: string(book-title);
        font-family: sans-serif;
        font-size: 9pt;
        font-style: italic;
    }}
}}

@page :first {{
    @top-left {{ content: none; }}
    @top-right {{ content: none; }}
    @bottom-left {{ content: none; }}
    @bottom-right {{ content: none; }}
    @bottom-center {{ content: none; }}
}}

@page title-page {{
    @top-left {{ content: none; }}
    @top-right {{ content: none; }}
    @bottom-left {{ content: none; }}
    @bottom-right {{ content: none; }}
}}

@page chapter-start {{
    @top-left {{ content: none; }}
    @top-right {{ content: none; }}
}}

/* Base typography */
body {{
    font-family: {cfg.font_family};
    font-size: {cfg.font_size};
    line-height: {cfg.line_height};
    text-align: justify;
    hyphens: auto;
}}

/* Title page */
.title-page {{
    page: title-page;
    page-break-after: always;
    text-align: center;
    padding-top: 30%;
}}

.title-page .book-title {{
    font-size: 2.5em;
    margin-bottom: 0.5em;
}}

.title-page .subtitle {{
    font-size: 1.5em;
    font-style: italic;
    margin-bottom: 2em;
}}

.title-page .author {{
    font-size: 1.3em;
    margin-bottom: 0.5em;
}}

.title-page .publisher {{
    font-size: 1em;
    margin-top: 3em;
}}

/* Copyright page */
.copyright-page {{
    page-break-after: always;
    font-size: 0.9em;
    padding-top: 60%;
}}

/* Table of contents */
.toc {{
    page-break-after: always;
}}

.toc h2 {{
    font-size: 1.5em;
    margin-bottom: 1em;
}}

.toc ol {{
    list-style: none;
    padding: 0;
}}

.toc li {{
    margin: 0.5em 0;
}}

.toc a {{
    text-decoration: none;
    color: inherit;
}}

.toc a::after {{
    content: leader('.') target-counter(attr(href), page);
}}

/* Chapters */
.chapter {{
    page-break-before: always;
}}

.chapter-title {{
    font-size: 2em;
    margin-top: 2in;
    margin-bottom: 1.5em;
    text-align: center;
    page: chapter-start;
    string-set: chapter-title content();
}}

/* Headings */
h1, h2, h3, h4, h5, h6 {{
    font-family: sans-serif;
    page-break-after: avoid;
    margin-top: 1.5em;
    margin-bottom: 0.5em;
}}

h2 {{ font-size: 1.4em; }}
h3 {{ font-size: 1.2em; }}
h4 {{ font-size: 1.1em; }}

/* Paragraphs */
p {{
    margin: 0;
    text-indent: 1.5em;
    widows: 2;
    orphans: 2;
}}

p:first-of-type,
h1 + p, h2 + p, h3 + p, h4 + p,
blockquote + p,
figure + p {{
    text-indent: 0;
}}

/* Blockquotes */
blockquote {{
    margin: 1em 2em;
    font-style: italic;
}}

/* Images */
figure {{
    margin: 1.5em auto;
    text-align: center;
    page-break-inside: avoid;
}}

figure img {{
    max-width: 100%;
    max-height: 6in;
    height: auto;
}}

figcaption {{
    font-size: 0.9em;
    font-style: italic;
    margin-top: 0.5em;
}}

/* Tables */
table {{
    width: 100%;
    border-collapse: collapse;
    margin: 1em 0;
    page-break-inside: avoid;
}}

th, td {{
    border: 0.5pt solid #333;
    padding: 0.4em 0.6em;
    text-align: left;
}}

th {{
    background-color: #f0f0f0;
    font-weight: bold;
}}

/* Code */
code {{
    font-family: "Courier New", Courier, monospace;
    font-size: 0.9em;
}}

pre {{
    font-family: "Courier New", Courier, monospace;
    font-size: 0.85em;
    background-color: #f5f5f5;
    padding: 1em;
    page-break-inside: avoid;
    white-space: pre-wrap;
}}

/* Links */
a {{
    color: inherit;
    text-decoration: none;
}}

/* Page break */
.page-break {{
    page-break-after: always;
}}

/* Horizontal rule */
hr {{
    border: none;
    border-top: 0.5pt solid #333;
    margin: 2em auto;
    width: 30%;
}}

/* Superscript and subscript */
sup, sub {{
    font-size: 0.75em;
    line-height: 0;
}}

sup {{ vertical-align: super; }}
sub {{ vertical-align: sub; }}

del {{
    text-decoration: line-through;
}}
"""
