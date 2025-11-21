"""
DOCX text extractor
"""
import io
from typing import Tuple
from services.extractors.base_extractor import BaseExtractor

try:
    from docx import Document
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False


class DOCXExtractor(BaseExtractor):
    """Extract text from DOCX files"""

    def extract(self, file_content: bytes, filename: str) -> Tuple[str, dict]:
        """Extract text from DOCX"""
        if not DOCX_AVAILABLE:
            raise ImportError("python-docx is not installed. Install it with: pip install python-docx")

        try:
            docx_file = io.BytesIO(file_content)
            doc = Document(docx_file)

            # Extract text from paragraphs
            paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]

            # Extract text from tables
            table_texts = []
            for table in doc.tables:
                for row in table.rows:
                    row_text = " | ".join([cell.text.strip() for cell in row.cells])
                    if row_text:
                        table_texts.append(row_text)

            all_text = paragraphs + table_texts
            extracted_text = "\n\n".join(all_text)

            metadata = {
                "num_paragraphs": len(paragraphs),
                "num_tables": len(doc.tables),
                "extractor": "python-docx"
            }

            # Try to get document properties
            try:
                core_properties = doc.core_properties
                metadata["author"] = core_properties.author or ""
                metadata["title"] = core_properties.title or ""
                metadata["subject"] = core_properties.subject or ""
            except:
                pass

            return extracted_text.strip(), metadata

        except Exception as e:
            raise Exception(f"Failed to extract text from DOCX: {str(e)}")

    def supports(self, file_format: str) -> bool:
        """Check if format is DOCX"""
        return file_format.lower() in ["docx", "doc"]
