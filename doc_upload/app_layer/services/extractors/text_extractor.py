"""
Plain text extractor
"""
from typing import Tuple
from services.extractors.base_extractor import BaseExtractor


class TextExtractor(BaseExtractor):
    """Extract text from plain text files"""

    SUPPORTED_FORMATS = ["txt", "csv", "json", "xml", "html", "md", "rtf"]

    def extract(self, file_content: bytes, filename: str) -> Tuple[str, dict]:
        """Extract text from plain text files"""
        try:
            # Try different encodings
            encodings = ["utf-8", "latin-1", "cp1252", "iso-8859-1"]
            extracted_text = None

            for encoding in encodings:
                try:
                    extracted_text = file_content.decode(encoding)
                    break
                except UnicodeDecodeError:
                    continue

            if extracted_text is None:
                raise Exception("Failed to decode file with common encodings")

            metadata = {
                "extractor": "TextExtractor",
                "encoding": encoding,
                "line_count": len(extracted_text.split("\n"))
            }

            return extracted_text.strip(), metadata

        except Exception as e:
            raise Exception(f"Failed to extract text: {str(e)}")

    def supports(self, file_format: str) -> bool:
        """Check if format is supported text format"""
        return file_format.lower() in self.SUPPORTED_FORMATS
