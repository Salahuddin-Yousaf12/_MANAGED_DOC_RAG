"""
Extractor factory to get the right extractor for a file format
"""
from typing import List
from services.extractors.base_extractor import BaseExtractor
from services.extractors.pdf_extractor import PDFExtractor
from services.extractors.docx_extractor import DOCXExtractor
from services.extractors.text_extractor import TextExtractor


class ExtractorFactory:
    """Factory to get the appropriate text extractor"""

    def __init__(self):
        self.extractors: List[BaseExtractor] = [
            PDFExtractor(),
            DOCXExtractor(),
            TextExtractor()
        ]

    def get_extractor(self, file_format: str) -> BaseExtractor:
        """
        Get the appropriate extractor for a file format

        Args:
            file_format: File extension (e.g., 'pdf', 'docx')

        Returns:
            BaseExtractor instance

        Raises:
            ValueError: If no extractor supports the format
        """
        for extractor in self.extractors:
            if extractor.supports(file_format):
                return extractor

        raise ValueError(f"No extractor available for format: {file_format}")

    def is_supported(self, file_format: str) -> bool:
        """
        Check if a file format is supported

        Args:
            file_format: File extension

        Returns:
            True if supported, False otherwise
        """
        try:
            self.get_extractor(file_format)
            return True
        except ValueError:
            return False
