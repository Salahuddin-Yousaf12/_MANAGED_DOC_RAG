"""
PDF text extractor
"""
import io
from typing import Tuple
from services.extractors.base_extractor import BaseExtractor

try:
    import PyPDF2
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False


class PDFExtractor(BaseExtractor):
    """Extract text from PDF files"""

    def extract(self, file_content: bytes, filename: str) -> Tuple[str, dict]:
        """Extract text from PDF"""
        if not PDF_AVAILABLE:
            raise ImportError("PyPDF2 is not installed. Install it with: pip install PyPDF2")

        try:
            pdf_file = io.BytesIO(file_content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)

            text_content = []
            num_pages = len(pdf_reader.pages)

            for page_num in range(num_pages):
                page = pdf_reader.pages[page_num]
                text_content.append(page.extract_text())

            extracted_text = "\n\n".join(text_content)

            metadata = {
                "num_pages": num_pages,
                "extractor": "PyPDF2"
            }

            # Try to get PDF metadata
            if pdf_reader.metadata:
                metadata["author"] = pdf_reader.metadata.get("/Author", "")
                metadata["title"] = pdf_reader.metadata.get("/Title", "")
                metadata["subject"] = pdf_reader.metadata.get("/Subject", "")

            return extracted_text.strip(), metadata

        except Exception as e:
            raise Exception(f"Failed to extract text from PDF: {str(e)}")

    def supports(self, file_format: str) -> bool:
        """Check if format is PDF"""
        return file_format.lower() == "pdf"
