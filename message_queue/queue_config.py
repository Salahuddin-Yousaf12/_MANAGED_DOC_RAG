"""
Shared configuration for Redis message queue.
Copy this file to both doc_upload and vector_service, or import as needed.

Message Flow:
1. doc_upload stores document in MongoDB
2. doc_upload publishes message to DOCUMENT_QUEUE with document_id
3. vector_service listens on DOCUMENT_QUEUE
4. vector_service fetches document from doc_upload and processes it
"""

# Redis Configuration
REDIS_HOST = "rag-redis"
REDIS_PORT = 6379
REDIS_DB = 0

# Queue Names
DOCUMENT_QUEUE = "document:process"  # Queue for new documents to process

# Message Format (JSON)
# {
#     "document_id": "uuid-string",
#     "filename": "example.pdf",
#     "timestamp": "2024-01-01T12:00:00Z"
# }
