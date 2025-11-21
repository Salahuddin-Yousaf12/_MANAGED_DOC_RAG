"""
Milvus repository for vector storage and retrieval
"""
from typing import List, Dict, Optional, Any
from uuid import UUID
from pymilvus import (
    connections,
    Collection,
    FieldSchema,
    CollectionSchema,
    DataType,
    utility
)
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class MilvusRepository:
    """
    Repository for Milvus vector database operations.
    Stores dense embeddings, sparse embeddings, and text chunks.
    """

    def __init__(self):
        self.host = settings.MILVUS_HOST
        self.port = settings.MILVUS_PORT
        self.collection_name = settings.MILVUS_COLLECTION_NAME
        self.dense_dim = settings.DENSE_EMBEDDING_DIM
        self._collection: Optional[Collection] = None
        self._connected = False

    async def connect(self):
        """Establish connection to Milvus"""
        try:
            connections.connect(
                alias="default",
                host=self.host,
                port=self.port
            )
            self._connected = True
            logger.info(f"Connected to Milvus at {self.host}:{self.port}")

            # Create collection if not exists
            await self._ensure_collection()

        except Exception as e:
            logger.error(f"Failed to connect to Milvus: {e}")
            raise

    async def disconnect(self):
        """Close Milvus connection"""
        try:
            connections.disconnect("default")
            self._connected = False
            logger.info("Disconnected from Milvus")
        except Exception as e:
            logger.error(f"Error disconnecting from Milvus: {e}")

    async def _ensure_collection(self):
        """Create collection if it doesn't exist"""
        if utility.has_collection(self.collection_name):
            self._collection = Collection(self.collection_name)
            self._collection.load()
            logger.info(f"Loaded existing collection: {self.collection_name}")
            return

        # Define schema
        fields = [
            FieldSchema(
                name="id",
                dtype=DataType.VARCHAR,
                is_primary=True,
                max_length=36
            ),
            FieldSchema(
                name="document_id",
                dtype=DataType.VARCHAR,
                max_length=36
            ),
            FieldSchema(
                name="chunk_index",
                dtype=DataType.INT64
            ),
            FieldSchema(
                name="text",
                dtype=DataType.VARCHAR,
                max_length=65535
            ),
            FieldSchema(
                name="dense_embedding",
                dtype=DataType.FLOAT_VECTOR,
                dim=self.dense_dim
            ),
            FieldSchema(
                name="sparse_embedding",
                dtype=DataType.SPARSE_FLOAT_VECTOR
            )
        ]

        schema = CollectionSchema(
            fields=fields,
            description="Document chunks with dense and sparse embeddings"
        )

        self._collection = Collection(
            name=self.collection_name,
            schema=schema
        )

        # Create indexes
        # Dense vector index (IVF_FLAT for good balance of speed/accuracy)
        dense_index_params = {
            "metric_type": "COSINE",
            "index_type": "IVF_FLAT",
            "params": {"nlist": 128}
        }
        self._collection.create_index(
            field_name="dense_embedding",
            index_params=dense_index_params
        )

        # Sparse vector index
        sparse_index_params = {
            "metric_type": "IP",
            "index_type": "SPARSE_INVERTED_INDEX",
            "params": {"drop_ratio_build": 0.2}
        }
        self._collection.create_index(
            field_name="sparse_embedding",
            index_params=sparse_index_params
        )

        self._collection.load()
        logger.info(f"Created and loaded collection: {self.collection_name}")

    @property
    def collection(self) -> Collection:
        """Get the collection, ensuring it's loaded"""
        if self._collection is None:
            raise RuntimeError("Milvus collection not initialized. Call connect() first.")
        return self._collection

    async def insert_chunks(
        self,
        ids: List[str],
        document_ids: List[str],
        chunk_indices: List[int],
        texts: List[str],
        dense_embeddings: List[List[float]],
        sparse_embeddings: List[Dict[int, float]]
    ) -> List[str]:
        """
        Insert document chunks with embeddings.

        Args:
            ids: Unique IDs for each chunk (match PostgreSQL)
            document_ids: Document IDs from MongoDB
            chunk_indices: Index of chunk within document
            texts: Text content of chunks
            dense_embeddings: Dense embedding vectors
            sparse_embeddings: Sparse embedding dictionaries

        Returns:
            List of inserted IDs
        """
        data = [
            ids,
            document_ids,
            chunk_indices,
            texts,
            dense_embeddings,
            sparse_embeddings
        ]

        self.collection.insert(data)
        self.collection.flush()

        logger.info(f"Inserted {len(ids)} chunks into Milvus")
        return ids

    async def search_dense(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        filter_expr: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search using dense embeddings.

        Args:
            query_embedding: Query vector
            top_k: Number of results
            filter_expr: Optional filter expression

        Returns:
            List of search results
        """
        search_params = {
            "metric_type": "COSINE",
            "params": {"nprobe": 16}
        }

        results = self.collection.search(
            data=[query_embedding],
            anns_field="dense_embedding",
            param=search_params,
            limit=top_k,
            expr=filter_expr,
            output_fields=["id", "document_id", "chunk_index", "text"]
        )

        return self._format_search_results(results[0])

    async def search_sparse(
        self,
        query_sparse: Dict[int, float],
        top_k: int = 10,
        filter_expr: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search using sparse embeddings.

        Args:
            query_sparse: Sparse query vector
            top_k: Number of results
            filter_expr: Optional filter expression

        Returns:
            List of search results
        """
        search_params = {
            "metric_type": "IP",
            "params": {"drop_ratio_search": 0.2}
        }

        results = self.collection.search(
            data=[query_sparse],
            anns_field="sparse_embedding",
            param=search_params,
            limit=top_k,
            expr=filter_expr,
            output_fields=["id", "document_id", "chunk_index", "text"]
        )

        return self._format_search_results(results[0])

    async def search_hybrid(
        self,
        query_dense: List[float],
        query_sparse: Dict[int, float],
        top_k: int = 10,
        dense_weight: float = 0.7,
        sparse_weight: float = 0.3,
        filter_expr: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Hybrid search combining dense and sparse results.

        Args:
            query_dense: Dense query vector
            query_sparse: Sparse query vector
            top_k: Number of results
            dense_weight: Weight for dense scores
            sparse_weight: Weight for sparse scores
            filter_expr: Optional filter expression

        Returns:
            List of combined search results
        """
        # Get more results from each to allow for merging
        fetch_k = min(top_k * 2, 100)

        # Run both searches
        dense_results = await self.search_dense(query_dense, fetch_k, filter_expr)
        sparse_results = await self.search_sparse(query_sparse, fetch_k, filter_expr)

        # Combine results using reciprocal rank fusion
        combined = self._reciprocal_rank_fusion(
            dense_results, sparse_results,
            dense_weight, sparse_weight
        )

        return combined[:top_k]

    def _format_search_results(self, hits) -> List[Dict[str, Any]]:
        """Format Milvus search results"""
        results = []
        for hit in hits:
            results.append({
                "id": hit.entity.get("id"),
                "document_id": hit.entity.get("document_id"),
                "chunk_index": hit.entity.get("chunk_index"),
                "text": hit.entity.get("text"),
                "score": hit.score
            })
        return results

    def _reciprocal_rank_fusion(
        self,
        dense_results: List[Dict],
        sparse_results: List[Dict],
        dense_weight: float,
        sparse_weight: float,
        k: int = 60
    ) -> List[Dict[str, Any]]:
        """
        Combine results using Reciprocal Rank Fusion.

        RRF score = sum(weight / (k + rank)) for each list
        """
        scores: Dict[str, float] = {}
        result_data: Dict[str, Dict] = {}

        # Process dense results
        for rank, result in enumerate(dense_results):
            chunk_id = result["id"]
            scores[chunk_id] = scores.get(chunk_id, 0) + dense_weight / (k + rank + 1)
            result_data[chunk_id] = result

        # Process sparse results
        for rank, result in enumerate(sparse_results):
            chunk_id = result["id"]
            scores[chunk_id] = scores.get(chunk_id, 0) + sparse_weight / (k + rank + 1)
            if chunk_id not in result_data:
                result_data[chunk_id] = result

        # Sort by combined score
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)

        combined_results = []
        for chunk_id in sorted_ids:
            result = result_data[chunk_id].copy()
            result["score"] = scores[chunk_id]
            combined_results.append(result)

        return combined_results

    async def delete_by_document_id(self, document_id: str) -> int:
        """
        Delete all chunks for a document.

        Args:
            document_id: Document ID to delete

        Returns:
            Number of deleted entities
        """
        expr = f'document_id == "{document_id}"'

        # Get count before deletion
        results = self.collection.query(
            expr=expr,
            output_fields=["id"]
        )
        count = len(results)

        if count > 0:
            self.collection.delete(expr)
            self.collection.flush()
            logger.info(f"Deleted {count} chunks for document {document_id}")

        return count

    async def get_by_document_id(self, document_id: str) -> List[Dict[str, Any]]:
        """
        Get all chunks for a document.

        Args:
            document_id: Document ID

        Returns:
            List of chunk data
        """
        expr = f'document_id == "{document_id}"'

        results = self.collection.query(
            expr=expr,
            output_fields=["id", "document_id", "chunk_index", "text"]
        )

        return results

    async def health_check(self) -> bool:
        """Check if Milvus connection is healthy"""
        try:
            return utility.has_collection(self.collection_name)
        except Exception:
            return False


# Global instance
milvus_repository = MilvusRepository()
