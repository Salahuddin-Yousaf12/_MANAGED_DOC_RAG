"""
Base text extractor interface
"""
from abc import ABC, abstractmethod
from typing import Tuple


class BaseExtractor(ABC):
    """Abstract base class for text extractors"""

    @abstractmethod
    def extract(self, file_content: bytes, filename: str) -> Tuple[str, dict]:
        """
        Extract text from file content

        Args:
            file_content: Raw file bytes
            filename: Original filename

        Returns:
            Tuple of (extracted_text, metadata_dict)
        """
        pass

    @abstractmethod
    def supports(self, file_format: str) -> bool:
        """
        Check if this extractor supports the given format

        Args:
            file_format: File extension (e.g., 'pdf', 'docx')

        Returns:
            True if format is supported, False otherwise
        """
        pass
