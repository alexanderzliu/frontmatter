"""Intermediate Representation node types."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class NodeType(Enum):
    """Types of nodes in the document IR."""

    # Block-level nodes
    DOCUMENT = "document"
    CHAPTER = "chapter"
    SECTION = "section"
    PARAGRAPH = "paragraph"
    HEADING = "heading"
    IMAGE = "image"
    TABLE = "table"
    TABLE_ROW = "table_row"
    TABLE_CELL = "table_cell"
    FOOTNOTE = "footnote"
    BLOCKQUOTE = "blockquote"
    LIST = "list"
    LIST_ITEM = "list_item"
    CODE_BLOCK = "code_block"
    HORIZONTAL_RULE = "horizontal_rule"
    PAGE_BREAK = "page_break"

    # Inline nodes
    TEXT = "text"
    EMPHASIS = "emphasis"
    STRONG = "strong"
    LINK = "link"
    FOOTNOTE_REF = "footnote_ref"
    CODE = "code"
    SUPERSCRIPT = "superscript"
    SUBSCRIPT = "subscript"
    STRIKETHROUGH = "strikethrough"


@dataclass
class Node:
    """Base node in the IR tree."""

    node_type: NodeType
    children: list["Node"] = field(default_factory=list)
    attributes: dict = field(default_factory=dict)

    def add_child(self, child: "Node") -> "Node":
        """Add a child node and return self for chaining."""
        self.children.append(child)
        return self

    def get_text(self) -> str:
        """Recursively extract all text content from this node."""
        if isinstance(self, TextNode):
            return self.text
        return "".join(child.get_text() for child in self.children)


@dataclass
class TextNode(Node):
    """Leaf node containing text content."""

    text: str = ""

    def __post_init__(self):
        self.node_type = NodeType.TEXT
        self.children = []

    def get_text(self) -> str:
        return self.text


@dataclass
class ImageNode(Node):
    """Image with source data and optional caption."""

    src: bytes = field(default_factory=bytes)
    mime_type: str = "image/png"
    alt_text: str = ""
    caption: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    filename: str = ""

    def __post_init__(self):
        self.node_type = NodeType.IMAGE
        self.children = []


@dataclass
class LinkNode(Node):
    """Hyperlink with URL."""

    url: str = ""
    title: Optional[str] = None

    def __post_init__(self):
        self.node_type = NodeType.LINK


@dataclass
class HeadingNode(Node):
    """Heading with level (1-6)."""

    level: int = 1

    def __post_init__(self):
        self.node_type = NodeType.HEADING


@dataclass
class ListNode(Node):
    """List (ordered or unordered)."""

    ordered: bool = False
    start: int = 1

    def __post_init__(self):
        self.node_type = NodeType.LIST


@dataclass
class TableNode(Node):
    """Table with rows and cells."""

    col_widths: list[Optional[int]] = field(default_factory=list)

    def __post_init__(self):
        self.node_type = NodeType.TABLE


@dataclass
class FootnoteNode(Node):
    """Footnote with reference ID."""

    ref_id: str = ""

    def __post_init__(self):
        self.node_type = NodeType.FOOTNOTE


@dataclass
class FootnoteRefNode(Node):
    """Reference to a footnote."""

    ref_id: str = ""
    number: int = 0

    def __post_init__(self):
        self.node_type = NodeType.FOOTNOTE_REF
        self.children = []


def paragraph(*children: Node) -> Node:
    """Helper to create a paragraph node."""
    return Node(node_type=NodeType.PARAGRAPH, children=list(children))


def text(content: str) -> TextNode:
    """Helper to create a text node."""
    return TextNode(node_type=NodeType.TEXT, text=content)


def strong(*children: Node) -> Node:
    """Helper to create a strong/bold node."""
    return Node(node_type=NodeType.STRONG, children=list(children))


def emphasis(*children: Node) -> Node:
    """Helper to create an emphasis/italic node."""
    return Node(node_type=NodeType.EMPHASIS, children=list(children))


def heading(level: int, *children: Node) -> HeadingNode:
    """Helper to create a heading node."""
    node = HeadingNode(node_type=NodeType.HEADING, level=level, children=list(children))
    return node
