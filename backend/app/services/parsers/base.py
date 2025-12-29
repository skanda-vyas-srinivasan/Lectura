"""Base parser interface for document parsing."""
from abc import ABC, abstractmethod
from typing import List
from pathlib import Path

from app.models import SlideContent


class BaseParser(ABC):
    """
    Abstract base class for document parsers.

    All parsers (PDF, PPTX, etc.) implement this interface to ensure
    consistent behavior and output format.
    """

    @abstractmethod
    def parse(self, file_path: str | Path) -> List[SlideContent]:
        """
        Parse a document file and extract slide content.

        Args:
            file_path: Path to the document file

        Returns:
            List of SlideContent objects, one per slide/page

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file format is invalid or corrupted
            Exception: For other parsing errors
        """
        pass

    @abstractmethod
    def validate_file(self, file_path: str | Path) -> bool:
        """
        Validate that the file exists and is the correct format.

        Args:
            file_path: Path to the document file

        Returns:
            True if file is valid, False otherwise
        """
        pass

    def get_file_info(self, file_path: str | Path) -> dict:
        """
        Get basic file information.

        Args:
            file_path: Path to the document file

        Returns:
            Dictionary with file metadata (size, format, etc.)
        """
        path = Path(file_path)
        return {
            "filename": path.name,
            "size_bytes": path.stat().st_size if path.exists() else 0,
            "extension": path.suffix.lower(),
            "exists": path.exists(),
        }
