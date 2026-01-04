"""Pydantic configuration models."""

from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, Field


class Margins(BaseModel):
    """Page margins configuration."""

    top: str = "0.75in"
    bottom: str = "0.75in"
    inside: str = "0.875in"  # Gutter for binding
    outside: str = "0.625in"


class PdfConfig(BaseModel):
    """PDF output configuration."""

    # Page setup
    page_size: str = "6in 9in"  # Common trade paperback
    margins: Margins = Field(default_factory=Margins)
    bleed: Optional[str] = "0.125in"
    crop_marks: bool = True

    # Typography
    font_family: str = "Georgia, serif"
    font_size: str = "11pt"
    line_height: float = 1.5

    # Headers/Footers
    show_page_numbers: bool = True
    page_number_position: Literal["bottom-center", "bottom-outside"] = "bottom-outside"
    show_running_headers: bool = True

    # Front matter
    include_title_page: bool = True
    include_copyright_page: bool = True
    include_toc: bool = True

    # Advanced
    embed_fonts: bool = True


class EpubConfig(BaseModel):
    """EPUB output configuration."""

    version: Literal["2.0", "3.0"] = "3.0"

    # Metadata
    language: str = "en"

    # Structure
    split_chapters: bool = True
    include_toc: bool = True

    # Styling
    css_file: Optional[Path] = None
    font_size: str = "1em"

    # Cover
    cover_image: Optional[Path] = None
    generate_cover: bool = False


class MetadataConfig(BaseModel):
    """Book metadata configuration."""

    title: str = "Untitled"
    subtitle: Optional[str] = None
    authors: list[str] = Field(default_factory=list)
    publisher: Optional[str] = None
    publication_date: Optional[str] = None
    isbn_print: Optional[str] = None
    isbn_epub: Optional[str] = None
    language: str = "en"
    description: Optional[str] = None
    keywords: list[str] = Field(default_factory=list)
    copyright: Optional[str] = None


class StyleMapping(BaseModel):
    """Map Word styles to semantic elements."""

    chapter_heading_styles: list[str] = Field(
        default_factory=lambda: ["Heading 1", "Title", "Chapter"]
    )
    section_heading_styles: list[str] = Field(
        default_factory=lambda: ["Heading 2", "Heading 3", "Heading 4"]
    )
    body_styles: list[str] = Field(default_factory=lambda: ["Normal", "Body Text", "Body"])
    blockquote_styles: list[str] = Field(default_factory=lambda: ["Quote", "Block Text"])


class TypesetConfig(BaseModel):
    """Main configuration for typeset tool."""

    metadata: MetadataConfig = Field(default_factory=MetadataConfig)
    pdf: PdfConfig = Field(default_factory=PdfConfig)
    epub: EpubConfig = Field(default_factory=EpubConfig)
    style_mapping: StyleMapping = Field(default_factory=StyleMapping)

    # Output
    output_dir: Path = Path("./output")
