"""
Client for fetching documents from doc_upload service
"""
import httpx
from typing import Optional, Dict, Any
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class DocUploadClient:
    """
    HTTP client for communicating with the doc_upload service.
    Fetches document data via the doc_upload API.
    """

    def __init__(self):
        self.base_url = settings.DOC_UPLOAD_SERVICE_URL
        self.timeout = settings.DOC_UPLOAD_TIMEOUT

    async def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch a document from doc_upload service by ID.

        Args:
            document_id: The document ID from MongoDB

        Returns:
            Document data dict or None if not found
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/documents/{document_id}"
                )

                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 404:
                    logger.warning(f"Document {document_id} not found in doc_upload service")
                    return None
                else:
                    logger.error(
                        f"Error fetching document {document_id}: "
                        f"status={response.status_code}, detail={response.text}"
                    )
                    return None

        except httpx.TimeoutException:
            logger.error(f"Timeout fetching document {document_id} from doc_upload service")
            raise
        except httpx.RequestError as e:
            logger.error(f"Connection error to doc_upload service: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching document: {e}")
            raise

    async def health_check(self) -> bool:
        """Check if doc_upload service is healthy"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/health")
                return response.status_code == 200
        except Exception:
            return False


# Global instance
doc_upload_client = DocUploadClient()
