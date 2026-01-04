"""Intermediate Representation document model."""

from dataclasses import dataclass, field
from typing import Optional

from typeset.ir.nodes import Node


@dataclass
class Metadata:
    """Document metadata."""

    title: str = "Untitled"
    subtitle: Optional[str] = None
    authors: list[str] = field(default_factory=list)
    language: str = "en"
    publisher: Optional[str] = None
    publication_date: Optional[str] = None
    isbn: Optional[str] = None
    isbn_print: Optional[str] = None
    isbn_epub: Optional[str] = None
    description: Optional[str] = None
    keywords: list[str] = field(default_factory=list)
    copyright: Optional[str] = None
    cover_image: Optional[bytes] = None
    cover_mime_type: str = "image/jpeg"


@dataclass
class Chapter:
    """A chapter in the document."""

    title: str
    level: int = 1  # Heading level (1-6)
    content: list[Node] = field(default_factory=list)
    id: str = ""  # For TOC linking

    def __post_init__(self):
        if not self.id:
            # Generate ID from title
            self.id = self._slugify(self.title)

    def _slugify(self, text: str) -> str:
        """Convert text to URL-safe slug."""
        import re

        slug = text.lower()
        slug = re.sub(r"[^\w\s-]", "", slug)
        slug = re.sub(r"[\s_]+", "-", slug)
        slug = slug.strip("-")
        return slug or "chapter"


@dataclass
class Document:
    """Complete document IR."""

    metadata: Metadata = field(default_factory=Metadata)
    front_matter: list[Node] = field(default_factory=list)  # Title page, copyright, etc.
    chapters: list[Chapter] = field(default_factory=list)
    back_matter: list[Node] = field(default_factory=list)  # Appendices, index
    footnotes: dict[str, Node] = field(default_factory=dict)  # id -> footnote content
    images: dict[str, bytes] = field(default_factory=dict)  # id -> image data

    def get_all_content(self) -> list[Node]:
        """Get all content nodes in order."""
        all_nodes = []
        all_nodes.extend(self.front_matter)
        for chapter in self.chapters:
            all_nodes.extend(chapter.content)
        all_nodes.extend(self.back_matter)
        return all_nodes

    def word_count(self) -> int:
        """Estimate word count of the document."""
        total = 0
        for chapter in self.chapters:
            for node in chapter.content:
                text = node.get_text()
                total += len(text.split())
        return total
