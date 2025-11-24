"""
Redis Publisher - Publishes document IDs to queue after MongoDB storage.
"""
import redis
import json
import os
from datetime import datetime
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Configuration from environment
REDIS_HOST = os.getenv("REDIS_HOST", "rag-redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
DOCUMENT_QUEUE = "document:process"


class DocumentPublisher:
    """Publishes document processing messages to Redis queue."""

    def __init__(self):
        self._client: Optional[redis.Redis] = None

    def connect(self) -> bool:
        """Connect to Redis."""
        try:
            self._client = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                db=REDIS_DB,
                decode_responses=True,
                socket_connect_timeout=5
            )
            self._client.ping()
            logger.info(f"Connected to Redis at {REDIS_HOST}:{REDIS_PORT}")
            return True
        except redis.ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self._client = None
            return False
        except Exception as e:
            logger.error(f"Redis connection error: {e}")
            self._client = None
            return False

    def publish_document(self, document_id: str, filename: str) -> bool:
        """
        Publish a document processing message to the queue.

        Args:
            document_id: MongoDB document ID
            filename: Original filename

        Returns:
            True if published successfully
        """
        if not self._client:
            if not self.connect():
                logger.warning("Redis not available, skipping queue publish")
                return False

        try:
            message = {
                "document_id": document_id,
                "filename": filename,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }

            self._client.lpush(DOCUMENT_QUEUE, json.dumps(message))
            logger.info(f"Published document {document_id} ({filename}) to queue")
            return True

        except redis.RedisError as e:
            logger.error(f"Failed to publish message: {e}")
            return False

    def close(self):
        """Close Redis connection."""
        if self._client:
            self._client.close()
            self._client = None


# Global instance
document_publisher = DocumentPublisher()
