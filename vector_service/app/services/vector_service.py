"""
Main vector service that orchestrates chunking, embedding, and storage
"""
from typing import List, Dict, Any, Optional
from uuid import uuid4
from datetime import datetime
from dateutil import parser as date_parser
from app.services.chunking_service import chunking_service
from app.services.embedding_service import embedding_service
from app.services.doc_upload_client import doc_upload_client
from app.repositories.milvus_repository import milvus_repository
from app.repositories.postgres_repository import postgres_repository
from app.models.chunk import (
    ProcessRequest,
    ProcessResponse,
    SearchRequest,
    SearchResult,
    SearchResponse,
    DocumentInfo,
    DeleteResponse
)
import logging

logger = logging.getLogger(__name__)


class VectorService:
    """
    Main service for processing documents into vectors.
    Coordinates chunking, embedding generation, and storage in Milvus + PostgreSQL.
    """

    def __init__(self):
        self.chunking = chunking_service
        self.embedding = embedding_service
        self.milvus = milvus_repository
        self.postgres = postgres_repository
        self.doc_client = doc_upload_client

    async def process_document_by_id(self, document_id: str) -> ProcessResponse:
        """
        Fetch a document from doc_upload service by ID and process it.

        Args:
            document_id: Document ID from MongoDB (via doc_upload service)

        Returns:
            ProcessResponse with processing results
        """
        logger.info(f"Fetching document {document_id} from doc_upload service")

        # Fetch document from doc_upload service
        doc_data = await self.doc_client.get_document(document_id)

        if not doc_data:
            raise ValueError(f"Document {document_id} not found in doc_upload service")

        # Parse the document data
        # Handle both 'id' and '_id' field names
        doc_id = doc_data.get("id") or doc_data.get("_id")
        filename = doc_data.get("filename", "unknown")
        file_format = doc_data.get("file_format", "")
        text_content = doc_data.get("text_content", "")
        file_size = doc_data.get("file_size")

        # Parse upload timestamp
        upload_ts = doc_data.get("upload_timestamp")
        if isinstance(upload_ts, str):
            upload_timestamp = date_parser.parse(upload_ts)
        elif isinstance(upload_ts, datetime):
            upload_timestamp = upload_ts
        else:
            upload_timestamp = datetime.utcnow()

        metadata = doc_data.get("metadata", {})

        # Create ProcessRequest and process
        request = ProcessRequest(
            document_id=str(doc_id),
            filename=filename,
            file_format=file_format,
            text_content=text_content,
            file_size=file_size,
            upload_timestamp=upload_timestamp,
            metadata=metadata
        )

        return await self.process_document(request)

    async def process_document(self, request: ProcessRequest) -> ProcessResponse:
        """
        Process a document: chunk it, generate embeddings, and store in both databases.

        Args:
            request: ProcessRequest with document data from doc_upload service

        Returns:
            ProcessResponse with processing results
        """
        document_id = request.document_id
        logger.info(f"Processing document {document_id}: {request.filename}")

        # Step 1: Chunk the text
        chunks = self.chunking.chunk_text(request.text_content)

        if not chunks:
            logger.warning(f"No chunks generated for document {document_id}")
            return ProcessResponse(
                document_id=document_id,
                filename=request.filename,
                total_chunks=0,
                chunk_ids=[],
                status="warning",
                message="No chunks could be generated from the document"
            )

        logger.info(f"Generated {len(chunks)} chunks for document {document_id}")

        # Step 2: Extract texts and generate unique IDs for each chunk
        chunk_ids = [str(uuid4()) for _ in chunks]
        chunk_texts = [chunk[0] for chunk in chunks]

        # Step 3: Generate embeddings
        logger.info("Generating dense embeddings...")
        dense_embeddings = self.embedding.generate_dense_embeddings_batch(chunk_texts)

        logger.info("Generating sparse embeddings...")
        sparse_embeddings = self.embedding.generate_sparse_embeddings_batch(chunk_texts)

        # Step 4: Prepare metadata for PostgreSQL
        chunk_metadata_records = []
        for i, (chunk_text, start_char, end_char) in enumerate(chunks):
            chunk_metadata_records.append({
                "id": chunk_ids[i],
                "document_id": document_id,
                "chunk_index": i,
                "filename": request.filename,
                "file_format": request.file_format,
                "file_size": request.file_size,
                "upload_timestamp": request.upload_timestamp,
                "chunk_start_char": start_char,
                "chunk_end_char": end_char,
                "metadata": request.metadata
            })

        # Step 5: Store in Milvus
        logger.info("Storing vectors in Milvus...")
        await self.milvus.insert_chunks(
            ids=chunk_ids,
            document_ids=[document_id] * len(chunks),
            chunk_indices=list(range(len(chunks))),
            texts=chunk_texts,
            dense_embeddings=dense_embeddings,
            sparse_embeddings=sparse_embeddings
        )

        # Step 6: Store metadata in PostgreSQL
        logger.info("Storing metadata in PostgreSQL...")
        await self.postgres.insert_chunks_batch(chunk_metadata_records)

        # Step 7: Store document summary
        await self.postgres.insert_document_summary(
            document_id=document_id,
            filename=request.filename,
            file_format=request.file_format,
            file_size=request.file_size,
            total_chunks=len(chunks),
            upload_timestamp=request.upload_timestamp,
            metadata=request.metadata
        )

        logger.info(f"Successfully processed document {document_id} with {len(chunks)} chunks")

        return ProcessResponse(
            document_id=document_id,
            filename=request.filename,
            total_chunks=len(chunks),
            chunk_ids=chunk_ids,
            status="success",
            message=f"Document processed successfully with {len(chunks)} chunks"
        )

    async def search(self, request: SearchRequest) -> SearchResponse:
        """
        Search for relevant chunks using vector similarity.

        Args:
            request: SearchRequest with query and parameters

        Returns:
            SearchResponse with results
        """
        logger.info(f"Searching with query: {request.query[:50]}...")

        # Generate query embeddings
        query_dense = self.embedding.generate_dense_embedding(request.query)
        query_sparse = self.embedding.generate_sparse_embedding(request.query)

        # Build filter expression if metadata filters provided
        filter_expr = None
        if request.filter_metadata:
            filter_expr = self._build_filter_expression(request.filter_metadata)

        # Perform search based on type
        if request.search_type == "dense":
            milvus_results = await self.milvus.search_dense(
                query_dense, request.top_k, filter_expr
            )
        elif request.search_type == "sparse":
            milvus_results = await self.milvus.search_sparse(
                query_sparse, request.top_k, filter_expr
            )
        else:  # hybrid
            milvus_results = await self.milvus.search_hybrid(
                query_dense, query_sparse, request.top_k,
                request.dense_weight, request.sparse_weight, filter_expr
            )

        # Enrich with metadata from PostgreSQL
        chunk_ids = [r["id"] for r in milvus_results]
        metadata_map = await self.postgres.get_chunks_metadata_batch(chunk_ids)

        results = []
        for mr in milvus_results:
            chunk_id = mr["id"]
            pg_metadata = metadata_map.get(chunk_id, {})

            results.append(SearchResult(
                chunk_id=chunk_id,
                document_id=mr["document_id"],
                text=mr["text"],
                score=mr["score"],
                chunk_index=mr["chunk_index"],
                metadata={
                    "filename": pg_metadata.get("filename", ""),
                    "file_format": pg_metadata.get("file_format", ""),
                    "file_size": pg_metadata.get("file_size"),
                    "upload_timestamp": pg_metadata.get("upload_timestamp", ""),
                    **pg_metadata.get("metadata", {})
                }
            ))

        return SearchResponse(
            query=request.query,
            results=results,
            total_results=len(results),
            search_type=request.search_type
        )

    def _build_filter_expression(self, filters: Dict[str, Any]) -> Optional[str]:
        """Build Milvus filter expression from metadata filters"""
        conditions = []

        if "document_id" in filters:
            conditions.append(f'document_id == "{filters["document_id"]}"')

        # Add more filter conditions as needed

        return " && ".join(conditions) if conditions else None

    async def get_document_info(self, document_id: str) -> Optional[DocumentInfo]:
        """
        Get information about a processed document.

        Args:
            document_id: Document ID

        Returns:
            DocumentInfo or None if not found
        """
        summary = await self.postgres.get_document_summary(document_id)

        if not summary:
            return None

        return DocumentInfo(
            document_id=summary["document_id"],
            filename=summary["filename"],
            file_format=summary["file_format"],
            file_size=summary["file_size"],
            total_chunks=summary["total_chunks"],
            upload_timestamp=datetime.fromisoformat(summary["upload_timestamp"]),
            metadata=summary.get("metadata", {})
        )

    async def get_document_chunks(self, document_id: str) -> List[Dict[str, Any]]:
        """
        Get all chunks for a document with their text and metadata.

        Args:
            document_id: Document ID

        Returns:
            List of chunk data
        """
        # Get chunks from Milvus (has the text)
        milvus_chunks = await self.milvus.get_by_document_id(document_id)

        # Get metadata from PostgreSQL
        pg_chunks = await self.postgres.get_chunks_by_document_id(document_id)
        pg_map = {c["id"]: c for c in pg_chunks}

        # Combine data
        result = []
        for mc in sorted(milvus_chunks, key=lambda x: x["chunk_index"]):
            chunk_id = mc["id"]
            pg_data = pg_map.get(chunk_id, {})

            result.append({
                "id": chunk_id,
                "document_id": mc["document_id"],
                "chunk_index": mc["chunk_index"],
                "text": mc["text"],
                "metadata": pg_data
            })

        return result

    async def delete_document(self, document_id: str) -> DeleteResponse:
        """
        Delete all data for a document from both databases.

        Args:
            document_id: Document ID to delete

        Returns:
            DeleteResponse with deletion results
        """
        logger.info(f"Deleting document {document_id}")

        # Delete from Milvus
        milvus_deleted = await self.milvus.delete_by_document_id(document_id)

        # Delete from PostgreSQL
        pg_deleted = await self.postgres.delete_by_document_id(document_id)

        total_deleted = max(milvus_deleted, pg_deleted)

        if total_deleted == 0:
            return DeleteResponse(
                document_id=document_id,
                chunks_deleted=0,
                status="not_found",
                message="Document not found"
            )

        return DeleteResponse(
            document_id=document_id,
            chunks_deleted=total_deleted,
            status="success",
            message=f"Successfully deleted {total_deleted} chunks"
        )

    async def health_check(self) -> Dict[str, Any]:
        """
        Check health of all components.

        Returns:
            Health status dictionary
        """
        milvus_healthy = await self.milvus.health_check()
        postgres_healthy = await self.postgres.health_check()

        return {
            "milvus": "healthy" if milvus_healthy else "unhealthy",
            "postgres": "healthy" if postgres_healthy else "unhealthy",
            "embedding_model": self.embedding.model_name,
            "embedding_dimension": self.embedding.get_embedding_dimension(),
            "vocab_size": self.embedding.get_vocab_size()
        }


# Global instance
vector_service = VectorService()
