"""
Vector Service - FastAPI application for document vectorization
Handles chunking, embedding generation, and storage in Milvus + PostgreSQL
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.services.vector_service import vector_service
from app.repositories.milvus_repository import milvus_repository
from app.repositories.postgres_repository import postgres_repository
from app.redis_queue.subscriber import document_subscriber
from app.models.chunk import (
    ProcessRequest,
    ProcessResponse,
    SearchRequest,
    SearchResponse,
    DocumentInfo,
    DeleteResponse
)
from typing import List, Dict, Any
import logging
import asyncio

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def process_document_callback(document_id: str, filename: str) -> bool:
    """Callback for processing documents from Redis queue."""
    try:
        logger.info(f"Processing document from queue: {document_id} ({filename})")
        result = await vector_service.process_document_by_id(document_id)
        logger.info(f"Document {document_id} processed: {result.chunks_created} chunks created")
        return True
    except Exception as e:
        logger.error(f"Failed to process document {document_id}: {e}")
        return False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle - startup and shutdown"""
    # Startup
    logger.info("Starting Vector Service...")
    worker_task = None

    try:
        # Connect to Milvus
        logger.info("Connecting to Milvus...")
        await milvus_repository.connect()

        # Connect to PostgreSQL
        logger.info("Connecting to PostgreSQL...")
        await postgres_repository.connect()

        # Start Redis queue worker
        logger.info("Starting Redis queue worker...")
        worker_task = asyncio.create_task(
            document_subscriber.start_worker(process_document_callback)
        )

        logger.info("Vector Service started successfully")
        yield

    except Exception as e:
        logger.error(f"Failed to start Vector Service: {e}")
        raise

    finally:
        # Shutdown
        logger.info("Shutting down Vector Service...")

        # Stop Redis worker
        if worker_task:
            document_subscriber.stop()
            worker_task.cancel()
            try:
                await worker_task
            except asyncio.CancelledError:
                pass
        document_subscriber.close()

        await milvus_repository.disconnect()
        await postgres_repository.disconnect()
        logger.info("Vector Service shutdown complete")


app = FastAPI(
    title="Vector Service",
    version="1.0.0",
    description="Document vectorization service with semantic chunking and hybrid search",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint with service information"""
    return {
        "service": "Vector Service",
        "version": "1.0.0",
        "description": "Document vectorization with Milvus and PostgreSQL",
        "endpoints": {
            "health": "GET /health",
            "process_with_data": "POST /api/v1/vectors/process",
            "process_by_id": "POST /api/v1/vectors/process/{document_id}",
            "search": "POST /api/v1/vectors/search",
            "get_document": "GET /api/v1/vectors/documents/{document_id}",
            "get_chunks": "GET /api/v1/vectors/documents/{document_id}/chunks",
            "delete": "DELETE /api/v1/vectors/documents/{document_id}"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        health = await vector_service.health_check()
        status = "healthy" if all(
            v == "healthy" for k, v in health.items()
            if k in ["milvus", "postgres"]
        ) else "degraded"

        return {
            "status": status,
            "service": "Vector Service",
            "components": health
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "Vector Service",
            "error": str(e)
        }


@app.post("/api/v1/vectors/process", response_model=ProcessResponse)
async def process_document(request: ProcessRequest):
    """
    Process a document with provided data.

    This endpoint receives document data, chunks the text semantically,
    generates dense and sparse embeddings, and stores everything in
    Milvus (vectors + text) and PostgreSQL (metadata).

    Args:
        request: ProcessRequest containing:
            - document_id: ID from MongoDB
            - filename: Original filename
            - file_format: File extension
            - text_content: Extracted text to process
            - file_size: Size in bytes (optional)
            - upload_timestamp: When uploaded
            - metadata: Additional metadata dict

    Returns:
        ProcessResponse with chunk IDs and status
    """
    try:
        result = await vector_service.process_document(request)
        return result
    except Exception as e:
        logger.error(f"Error processing document: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process document: {str(e)}"
        )


@app.post("/api/v1/vectors/process/{document_id}", response_model=ProcessResponse)
async def process_document_by_id(document_id: str):
    """
    Fetch and process a document from doc_upload service by ID.

    This endpoint fetches the document from doc_upload service using
    its GET /api/v1/documents/{id} endpoint, then chunks the text,
    generates embeddings, and stores in Milvus + PostgreSQL.

    Args:
        document_id: Document ID from MongoDB (via doc_upload service)

    Returns:
        ProcessResponse with chunk IDs and status
    """
    try:
        result = await vector_service.process_document_by_id(document_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error processing document {document_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process document: {str(e)}"
        )


@app.post("/api/v1/vectors/search", response_model=SearchResponse)
async def search_vectors(request: SearchRequest):
    """
    Search for relevant document chunks.

    Supports three search modes:
    - dense: Semantic similarity using dense embeddings
    - sparse: Keyword matching using BM25-style sparse embeddings
    - hybrid: Combined search with configurable weights (default)

    Args:
        request: SearchRequest containing:
            - query: Search query text
            - top_k: Number of results (1-100, default 10)
            - filter_metadata: Optional filters (e.g., document_id)
            - search_type: "dense", "sparse", or "hybrid"
            - dense_weight: Weight for dense scores (0-1, default 0.7)
            - sparse_weight: Weight for sparse scores (0-1, default 0.3)

    Returns:
        SearchResponse with ranked results including text and metadata
    """
    try:
        result = await vector_service.search(request)
        return result
    except Exception as e:
        logger.error(f"Error searching: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )


@app.get("/api/v1/vectors/documents/{document_id}", response_model=DocumentInfo)
async def get_document_info(document_id: str):
    """
    Get information about a processed document.

    Args:
        document_id: Document ID (from MongoDB)

    Returns:
        DocumentInfo with filename, format, chunk count, etc.
    """
    try:
        info = await vector_service.get_document_info(document_id)
        if not info:
            raise HTTPException(
                status_code=404,
                detail=f"Document {document_id} not found"
            )
        return info
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document info: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get document info: {str(e)}"
        )


@app.get("/api/v1/vectors/documents/{document_id}/chunks")
async def get_document_chunks(document_id: str) -> List[Dict[str, Any]]:
    """
    Get all chunks for a document with text and metadata.

    Args:
        document_id: Document ID

    Returns:
        List of chunks with text, index, and metadata
    """
    try:
        chunks = await vector_service.get_document_chunks(document_id)
        if not chunks:
            raise HTTPException(
                status_code=404,
                detail=f"No chunks found for document {document_id}"
            )
        return chunks
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document chunks: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get document chunks: {str(e)}"
        )


@app.delete("/api/v1/vectors/documents/{document_id}", response_model=DeleteResponse)
async def delete_document(document_id: str):
    """
    Delete a document and all its chunks from both databases.

    Args:
        document_id: Document ID to delete

    Returns:
        DeleteResponse with deletion status
    """
    try:
        result = await vector_service.delete_document(document_id)
        if result.status == "not_found":
            raise HTTPException(
                status_code=404,
                detail=f"Document {document_id} not found"
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete document: {str(e)}"
        )


# Additional utility endpoints for the retrieval service

@app.get("/api/v1/vectors/stats")
async def get_stats():
    """
    Get statistics about the vector store.

    Returns:
        Statistics including document count, chunk count, etc.
    """
    try:
        health = await vector_service.health_check()
        return {
            "embedding_model": health.get("embedding_model"),
            "embedding_dimension": health.get("embedding_dimension"),
            "vocab_size": health.get("vocab_size"),
            "status": "operational"
        }
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get stats: {str(e)}"
        )
