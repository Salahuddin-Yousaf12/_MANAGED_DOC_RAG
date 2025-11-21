"""
Document service - Business logic layer
"""
import os
from typing import Tuple
from models.document import Document, DocumentResponse
from repositories.document_repository import document_repository
from services.extractors.extractor_factory import ExtractorFactory


class DocumentService:
    """Service for document processing business logic"""

    def __init__(self):
        self.extractor_factory = ExtractorFactory()

    def _get_file_format(self, filename: str) -> str:
        """Extract file format from filename"""
        return os.path.splitext(filename)[1].lstrip('.').lower()

    async def process_and_store_document(
        self,
        file_content: bytes,
        filename: str,
        file_size: int
    ) -> DocumentResponse:
        """
        Process uploaded file and store in MongoDB

        Args:
            file_content: Raw file bytes
            filename: Original filename
            file_size: File size in bytes

        Returns:
            DocumentResponse with document ID and status

        Raises:
            ValueError: If file format is not supported
            Exception: If processing or storage fails
        """
        # Get file format
        file_format = self._get_file_format(filename)

        # Validate format is supported
        if not self.extractor_factory.is_supported(file_format):
            raise ValueError(
                f"Unsupported file format: {file_format}. "
                f"Please upload a supported file type."
            )

        try:
            # Extract text using appropriate extractor
            extractor = self.extractor_factory.get_extractor(file_format)
            text_content, metadata = extractor.extract(file_content, filename)

            # Create document model
            document = Document(
                filename=filename,
                file_format=file_format,
                text_content=text_content,
                file_size=file_size,
                metadata=metadata
            )

            # Store in MongoDB
            doc_id = await document_repository.create_document(document)

            # Return response
            return DocumentResponse(
                id=doc_id,
                filename=filename,
                file_format=file_format,
                file_size=file_size,
                upload_timestamp=document.upload_timestamp,
                status="success",
                message=f"Document processed and stored successfully. ID: {doc_id}"
            )

        except Exception as e:
            raise Exception(f"Failed to process document: {str(e)}")

    async def get_document(self, document_id: str) -> dict:
        """
        Retrieve document by ID

        Args:
            document_id: Document ID

        Returns:
            Document data

        Raises:
            Exception: If document not found or retrieval fails
        """
        doc = await document_repository.get_document_by_id(document_id)
        if not doc:
            raise Exception(f"Document not found: {document_id}")
        return doc

    async def delete_document(self, document_id: str) -> bool:
        """
        Delete document by ID

        Args:
            document_id: Document ID

        Returns:
            True if deleted successfully

        Raises:
            Exception: If document not found
        """
        deleted = await document_repository.delete_document(document_id)
        if not deleted:
            raise Exception(f"Document not found: {document_id}")
        return True

    async def get_document_count(self) -> int:
        """Get total document count"""
        return await document_repository.count_documents()


# Global service instance
document_service = DocumentService()
