"""
Configuration settings for the document upload application layer
"""
import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # MongoDB Configuration
    MONGODB_URL: str = os.getenv("MONGODB_URL", "mongodb://mongodb:27017")
    MONGODB_DB_NAME: str = os.getenv("MONGODB_DB_NAME", "document_store")
    MONGODB_COLLECTION: str = os.getenv("MONGODB_COLLECTION", "documents")

    # Application Configuration
    APP_NAME: str = "Document Upload Service - Application Layer"
    APP_VERSION: str = "1.0.0"
    MAX_FILE_SIZE: int = 100 * 1024 * 1024  # 100MB

    # Supported file formats
    SUPPORTED_FORMATS: list = [
        "pdf", "docx", "doc", "txt", "xlsx", "xls",
        "pptx", "ppt", "csv", "html", "xml", "json",
        "md", "rtf", "odt", "png", "jpg", "jpeg", "tiff"
    ]

    class Config:
        case_sensitive = True


settings = Settings()
