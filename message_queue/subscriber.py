"""
Redis Subscriber/Worker - Used by vector_service.
Listens for document processing messages and triggers vectorization.
"""
import redis
import json
import os
import asyncio
from typing import Optional, Callable, Awaitable
import logging

logger = logging.getLogger(__name__)

# Configuration from environment or defaults
REDIS_HOST = os.getenv("REDIS_HOST", "rag-redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
DOCUMENT_QUEUE = "document:process"


class DocumentSubscriber:
    """Subscribes to document processing messages from Redis queue."""

    def __init__(self):
        self._client: Optional[redis.Redis] = None
        self._running = False

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
            # Test connection
            self._client.ping()
            logger.info(f"Connected to Redis at {REDIS_HOST}:{REDIS_PORT}")
            return True
        except redis.ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self._client = None
            return False

    async def start_worker(
        self,
        process_callback: Callable[[str, str], Awaitable[bool]]
    ):
        """
        Start the background worker that processes messages.

        Args:
            process_callback: Async function(document_id, filename) -> bool
                             Called for each document to process
        """
        if not self._client:
            if not self.connect():
                logger.error("Cannot start worker: Redis not connected")
                return

        self._running = True
        logger.info("Document processing worker started")

        while self._running:
            try:
                # BRPOP blocks until a message is available (5 second timeout)
                result = self._client.brpop(DOCUMENT_QUEUE, timeout=5)

                if result:
                    queue_name, message_json = result
                    message = json.loads(message_json)

                    document_id = message.get("document_id")
                    filename = message.get("filename", "unknown")

                    logger.info(f"Received message: processing document {document_id}")

                    try:
                        success = await process_callback(document_id, filename)
                        if success:
                            logger.info(f"Successfully processed document {document_id}")
                        else:
                            logger.warning(f"Failed to process document {document_id}")
                    except Exception as e:
                        logger.error(f"Error processing document {document_id}: {e}")

                else:
                    # Timeout, no message - just continue loop
                    await asyncio.sleep(0.1)

            except redis.ConnectionError as e:
                logger.error(f"Redis connection lost: {e}")
                await asyncio.sleep(5)
                self.connect()

            except Exception as e:
                logger.error(f"Worker error: {e}")
                await asyncio.sleep(1)

    def stop(self):
        """Stop the worker."""
        self._running = False
        logger.info("Document processing worker stopping")

    def close(self):
        """Close Redis connection."""
        self.stop()
        if self._client:
            self._client.close()
            self._client = None


# Global instance
document_subscriber = DocumentSubscriber()
