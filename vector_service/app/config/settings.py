"""
Configuration settings for Vector Service
"""
import os
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Milvus settings
    MILVUS_HOST: str = os.getenv("MILVUS_HOST", "localhost")
    MILVUS_PORT: int = int(os.getenv("MILVUS_PORT", "19530"))
    MILVUS_COLLECTION_NAME: str = os.getenv("MILVUS_COLLECTION_NAME", "document_chunks")

    # PostgreSQL settings
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", "5432"))
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "vectoruser")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "vectorpass")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "vector_metadata")

    # Embedding settings
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    DENSE_EMBEDDING_DIM: int = 384  # Dimension for all-MiniLM-L6-v2

    # Chunking settings
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "512"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "50"))
    MIN_CHUNK_SIZE: int = int(os.getenv("MIN_CHUNK_SIZE", "100"))

    # Doc upload service URL (for fetching documents)
    DOC_UPLOAD_SERVICE_URL: str = os.getenv("DOC_UPLOAD_SERVICE_URL", "http://api-gateway:8080")
    DOC_UPLOAD_TIMEOUT: int = int(os.getenv("DOC_UPLOAD_TIMEOUT", "30"))

    @property
    def postgres_url(self) -> str:
        """Get PostgreSQL connection URL"""
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @property
    def postgres_sync_url(self) -> str:
        """Get PostgreSQL sync connection URL"""
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
