"""
Document data model
"""
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
import uuid


class Document(BaseModel):
    """Document model for MongoDB storage"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    filename: str
    file_format: str
    text_content: str
    file_size: int
    upload_timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

    class Config:
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "filename": "sample.pdf",
                "file_format": "pdf",
                "text_content": "This is the extracted text...",
                "file_size": 102400,
                "upload_timestamp": "2025-01-15T10:30:00",
                "metadata": {"pages": 5, "author": "John Doe"}
            }
        }


class DocumentResponse(BaseModel):
    """Response model for document operations"""
    id: str
    filename: str
    file_format: str
    file_size: int
    upload_timestamp: datetime
    status: str
    message: Optional[str] = None
