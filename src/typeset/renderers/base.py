"""Base renderer class."""

from abc import ABC, abstractmethod
from pathlib import Path

from typeset.ir.document import Document


class BaseRenderer(ABC):
    """Abstract base class for document renderers."""

    @abstractmethod
    def render(self, document: Document, output_path: str | Path) -> None:
        """Render document to output file."""
        pass

    @abstractmethod
    def get_extension(self) -> str:
        """Get the file extension for this renderer's output."""
        pass
