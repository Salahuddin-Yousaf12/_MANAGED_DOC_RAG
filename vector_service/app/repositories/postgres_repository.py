"""
PostgreSQL repository for metadata storage
"""
from typing import List, Dict, Optional, Any
from uuid import UUID
from datetime import datetime
import asyncpg
from app.config import settings
import logging
import json

logger = logging.getLogger(__name__)


class PostgresRepository:
    """
    Repository for PostgreSQL metadata storage.
    Stores chunk metadata that corresponds to vectors in Milvus.
    """

    def __init__(self):
        self.host = settings.POSTGRES_HOST
        self.port = settings.POSTGRES_PORT
        self.user = settings.POSTGRES_USER
        self.password = settings.POSTGRES_PASSWORD
        self.database = settings.POSTGRES_DB
        self._pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        """Create connection pool"""
        try:
            self._pool = await asyncpg.create_pool(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
                min_size=2,
                max_size=10
            )
            logger.info(f"Connected to PostgreSQL at {self.host}:{self.port}")
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            raise

    async def disconnect(self):
        """Close connection pool"""
        if self._pool:
            await self._pool.close()
            logger.info("Disconnected from PostgreSQL")

    @property
    def pool(self) -> asyncpg.Pool:
        """Get the connection pool"""
        if self._pool is None:
            raise RuntimeError("PostgreSQL pool not initialized. Call connect() first.")
        return self._pool

    async def insert_chunk_metadata(
        self,
        id: str,
        document_id: str,
        chunk_index: int,
        filename: str,
        file_format: str,
        file_size: Optional[int],
        upload_timestamp: datetime,
        chunk_start_char: Optional[int],
        chunk_end_char: Optional[int],
        metadata: Dict[str, Any]
    ) -> str:
        """
        Insert a single chunk metadata record.

        Args:
            id: Unique chunk ID (matches Milvus)
            document_id: Document ID from MongoDB
            chunk_index: Index within the document
            filename: Original filename
            file_format: File format/extension
            file_size: File size in bytes
            upload_timestamp: When document was uploaded
            chunk_start_char: Start position in original text
            chunk_end_char: End position in original text
            metadata: Additional metadata JSON

        Returns:
            Inserted ID
        """
        query = """
            INSERT INTO chunk_metadata (
                id, document_id, chunk_index, filename, file_format,
                file_size, upload_timestamp, chunk_start_char, chunk_end_char, metadata
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            RETURNING id
        """

        async with self.pool.acquire() as conn:
            result = await conn.fetchval(
                query,
                UUID(id),
                UUID(document_id),
                chunk_index,
                filename,
                file_format,
                file_size,
                upload_timestamp,
                chunk_start_char,
                chunk_end_char,
                json.dumps(metadata)
            )
            return str(result)

    async def insert_chunks_batch(
        self,
        chunks: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Insert multiple chunk metadata records.

        Args:
            chunks: List of chunk dictionaries with keys:
                - id, document_id, chunk_index, filename, file_format,
                - file_size, upload_timestamp, chunk_start_char, chunk_end_char, metadata

        Returns:
            List of inserted IDs
        """
        query = """
            INSERT INTO chunk_metadata (
                id, document_id, chunk_index, filename, file_format,
                file_size, upload_timestamp, chunk_start_char, chunk_end_char, metadata
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
        """

        records = [
            (
                UUID(c["id"]),
                UUID(c["document_id"]),
                c["chunk_index"],
                c["filename"],
                c["file_format"],
                c.get("file_size"),
                c["upload_timestamp"],
                c.get("chunk_start_char"),
                c.get("chunk_end_char"),
                json.dumps(c.get("metadata", {}))
            )
            for c in chunks
        ]

        async with self.pool.acquire() as conn:
            await conn.executemany(query, records)

        logger.info(f"Inserted {len(chunks)} chunk metadata records")
        return [c["id"] for c in chunks]

    async def insert_document_summary(
        self,
        document_id: str,
        filename: str,
        file_format: str,
        file_size: Optional[int],
        total_chunks: int,
        upload_timestamp: datetime,
        metadata: Dict[str, Any]
    ) -> str:
        """
        Insert or update document summary.

        Args:
            document_id: Document ID
            filename: Original filename
            file_format: File format
            file_size: File size in bytes
            total_chunks: Number of chunks
            upload_timestamp: Upload timestamp
            metadata: Additional metadata

        Returns:
            Document ID
        """
        query = """
            INSERT INTO document_summary (
                document_id, filename, file_format, file_size,
                total_chunks, upload_timestamp, metadata
            ) VALUES ($1, $2, $3, $4, $5, $6, $7)
            ON CONFLICT (document_id) DO UPDATE SET
                filename = EXCLUDED.filename,
                file_format = EXCLUDED.file_format,
                file_size = EXCLUDED.file_size,
                total_chunks = EXCLUDED.total_chunks,
                upload_timestamp = EXCLUDED.upload_timestamp,
                metadata = EXCLUDED.metadata
            RETURNING document_id
        """

        async with self.pool.acquire() as conn:
            result = await conn.fetchval(
                query,
                UUID(document_id),
                filename,
                file_format,
                file_size,
                total_chunks,
                upload_timestamp,
                json.dumps(metadata)
            )
            return str(result)

    async def get_chunk_metadata(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a specific chunk.

        Args:
            chunk_id: Chunk ID

        Returns:
            Chunk metadata or None
        """
        query = """
            SELECT id, document_id, chunk_index, filename, file_format,
                   file_size, upload_timestamp, chunk_start_char, chunk_end_char, metadata
            FROM chunk_metadata
            WHERE id = $1
        """

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, UUID(chunk_id))

        if row:
            return self._row_to_dict(row)
        return None

    async def get_chunks_by_document_id(
        self,
        document_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get all chunk metadata for a document.

        Args:
            document_id: Document ID

        Returns:
            List of chunk metadata
        """
        query = """
            SELECT id, document_id, chunk_index, filename, file_format,
                   file_size, upload_timestamp, chunk_start_char, chunk_end_char, metadata
            FROM chunk_metadata
            WHERE document_id = $1
            ORDER BY chunk_index
        """

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, UUID(document_id))

        return [self._row_to_dict(row) for row in rows]

    async def get_chunks_metadata_batch(
        self,
        chunk_ids: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get metadata for multiple chunks.

        Args:
            chunk_ids: List of chunk IDs

        Returns:
            Dictionary mapping chunk_id to metadata
        """
        if not chunk_ids:
            return {}

        query = """
            SELECT id, document_id, chunk_index, filename, file_format,
                   file_size, upload_timestamp, chunk_start_char, chunk_end_char, metadata
            FROM chunk_metadata
            WHERE id = ANY($1)
        """

        uuids = [UUID(cid) for cid in chunk_ids]

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, uuids)

        return {str(row["id"]): self._row_to_dict(row) for row in rows}

    async def get_document_summary(
        self,
        document_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get document summary.

        Args:
            document_id: Document ID

        Returns:
            Document summary or None
        """
        query = """
            SELECT document_id, filename, file_format, file_size,
                   total_chunks, upload_timestamp, metadata, created_at
            FROM document_summary
            WHERE document_id = $1
        """

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, UUID(document_id))

        if row:
            return {
                "document_id": str(row["document_id"]),
                "filename": row["filename"],
                "file_format": row["file_format"],
                "file_size": row["file_size"],
                "total_chunks": row["total_chunks"],
                "upload_timestamp": row["upload_timestamp"].isoformat(),
                "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
                "created_at": row["created_at"].isoformat()
            }
        return None

    async def delete_by_document_id(self, document_id: str) -> int:
        """
        Delete all chunks and summary for a document.

        Args:
            document_id: Document ID

        Returns:
            Number of deleted chunk records
        """
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                # Delete chunks
                result = await conn.execute(
                    "DELETE FROM chunk_metadata WHERE document_id = $1",
                    UUID(document_id)
                )
                # Extract count from result string like "DELETE 5"
                count = int(result.split()[-1])

                # Delete summary
                await conn.execute(
                    "DELETE FROM document_summary WHERE document_id = $1",
                    UUID(document_id)
                )

        logger.info(f"Deleted {count} chunk records for document {document_id}")
        return count

    async def search_by_metadata(
        self,
        filters: Dict[str, Any],
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Search chunks by metadata filters.

        Args:
            filters: Dictionary of filters (supports file_format, filename patterns)
            limit: Maximum results

        Returns:
            List of matching chunk metadata
        """
        conditions = []
        params = []
        param_count = 0

        if "file_format" in filters:
            param_count += 1
            conditions.append(f"file_format = ${param_count}")
            params.append(filters["file_format"])

        if "filename_like" in filters:
            param_count += 1
            conditions.append(f"filename ILIKE ${param_count}")
            params.append(f"%{filters['filename_like']}%")

        if "document_id" in filters:
            param_count += 1
            conditions.append(f"document_id = ${param_count}")
            params.append(UUID(filters["document_id"]))

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        param_count += 1
        query = f"""
            SELECT id, document_id, chunk_index, filename, file_format,
                   file_size, upload_timestamp, chunk_start_char, chunk_end_char, metadata
            FROM chunk_metadata
            WHERE {where_clause}
            LIMIT ${param_count}
        """
        params.append(limit)

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

        return [self._row_to_dict(row) for row in rows]

    def _row_to_dict(self, row: asyncpg.Record) -> Dict[str, Any]:
        """Convert database row to dictionary"""
        return {
            "id": str(row["id"]),
            "document_id": str(row["document_id"]),
            "chunk_index": row["chunk_index"],
            "filename": row["filename"],
            "file_format": row["file_format"],
            "file_size": row["file_size"],
            "upload_timestamp": row["upload_timestamp"].isoformat(),
            "chunk_start_char": row["chunk_start_char"],
            "chunk_end_char": row["chunk_end_char"],
            "metadata": json.loads(row["metadata"]) if row["metadata"] else {}
        }

    async def health_check(self) -> bool:
        """Check if PostgreSQL connection is healthy"""
        try:
            async with self.pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            return True
        except Exception:
            return False


# Global instance
postgres_repository = PostgresRepository()
