"""
Data models for vector service
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID, uuid4


class ChunkMetadata(BaseModel):
    """Metadata for a document chunk stored in PostgreSQL"""
    id: UUID = Field(default_factory=uuid4)
    document_id: UUID
    chunk_index: int
    filename: str
    file_format: str
    file_size: Optional[int] = None
    upload_timestamp: datetime
    chunk_start_char: Optional[int] = None
    chunk_end_char: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        from_attributes = True


class DocumentChunk(BaseModel):
    """Complete chunk data including text and embeddings"""
    id: UUID = Field(default_factory=uuid4)
    document_id: UUID
    chunk_index: int
    text: str
    dense_embedding: Optional[List[float]] = None
    sparse_embedding: Optional[Dict[int, float]] = None  # Index -> value for sparse vector
    metadata: ChunkMetadata


class ProcessRequest(BaseModel):
    """Request to process a document from doc_upload service"""
    document_id: str
    filename: str
    file_format: str
    text_content: str
    file_size: Optional[int] = None
    upload_timestamp: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ProcessResponse(BaseModel):
    """Response after processing a document"""
    document_id: str
    filename: str
    total_chunks: int
    chunk_ids: List[str]
    status: str = "success"
    message: str = "Document processed successfully"


class SearchRequest(BaseModel):
    """Request for vector search"""
    query: str
    top_k: int = Field(default=10, ge=1, le=100)
    filter_metadata: Optional[Dict[str, Any]] = None
    search_type: str = Field(default="hybrid", pattern="^(dense|sparse|hybrid)$")
    # Weights for hybrid search
    dense_weight: float = Field(default=0.7, ge=0, le=1)
    sparse_weight: float = Field(default=0.3, ge=0, le=1)


class SearchResult(BaseModel):
    """Single search result"""
    chunk_id: str
    document_id: str
    text: str
    score: float
    chunk_index: int
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    """Response from vector search"""
    query: str
    results: List[SearchResult]
    total_results: int
    search_type: str


class DocumentInfo(BaseModel):
    """Document information response"""
    document_id: str
    filename: str
    file_format: str
    file_size: Optional[int]
    total_chunks: int
    upload_timestamp: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DeleteResponse(BaseModel):
    """Response after deleting a document"""
    document_id: str
    chunks_deleted: int
    status: str = "success"
    message: str = "Document deleted successfully"
