"""
Application Layer - Main FastAPI application
This layer handles business logic and data access
"""
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import os

from config.settings import settings
from services.document_service import document_service
from repositories.document_repository import document_repository
from models.document import DocumentResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup: Connect to MongoDB
    await document_repository.connect()
    yield
    # Shutdown: Disconnect from MongoDB
    await document_repository.disconnect()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan
)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        doc_count = await document_service.get_document_count()
        return {
            "status": "healthy",
            "service": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "mongodb_connected": True,
            "document_count": doc_count,
            "container_id": os.getenv("HOSTNAME", "unknown")
        }
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "service": settings.APP_NAME,
                "error": str(e)
            }
        )


@app.post("/process", response_model=DocumentResponse)
async def process_document(file: UploadFile = File(...)):
    """
    Process uploaded document and store in MongoDB

    Args:
        file: Uploaded file

    Returns:
        DocumentResponse with document ID and status
    """
    try:
        # Read file content
        file_content = await file.read()
        file_size = len(file_content)

        # Validate file size
        if file_size > settings.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size: {settings.MAX_FILE_SIZE / (1024*1024)}MB"
            )

        if file_size == 0:
            raise HTTPException(
                status_code=400,
                detail="Empty file uploaded"
            )

        # Process and store document
        response = await document_service.process_and_store_document(
            file_content=file_content,
            filename=file.filename,
            file_size=file_size
        )

        return response

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/document/{document_id}")
async def get_document(document_id: str):
    """
    Retrieve document by ID

    Args:
        document_id: Document ID

    Returns:
        Document data
    """
    try:
        document = await document_service.get_document(document_id)
        return document
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.delete("/document/{document_id}")
async def delete_document(document_id: str):
    """
    Delete document by ID

    Args:
        document_id: Document ID

    Returns:
        Success message
    """
    try:
        await document_service.delete_document(document_id)
        return {"status": "success", "message": f"Document {document_id} deleted"}
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "endpoints": {
            "health": "/health",
            "process": "POST /process",
            "get_document": "GET /document/{id}",
            "delete_document": "DELETE /document/{id}"
        }
    }
