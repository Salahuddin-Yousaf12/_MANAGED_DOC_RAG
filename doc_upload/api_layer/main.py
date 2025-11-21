"""
API Layer - Entry point for external clients
This layer forwards requests to the application layer through Nginx load balancer
"""
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
import httpx
import os


# Application layer URL (goes through Nginx load balancer)
APP_LAYER_URL = os.getenv("APP_LAYER_URL", "http://nginx:80")

app = FastAPI(
    title="Document Upload Service - API Layer",
    version="1.0.0",
    description="API Gateway for document upload microservice"
)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check if app layer is reachable
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{APP_LAYER_URL}/health", timeout=5.0)
            app_layer_status = response.json()

        return {
            "status": "healthy",
            "service": "API Layer",
            "app_layer_status": app_layer_status
        }
    except Exception as e:
        return {
            "status": "degraded",
            "service": "API Layer",
            "error": str(e)
        }


@app.post("/api/v1/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    """
    Upload and process document

    Args:
        file: Document file to upload

    Returns:
        Document processing result with ID
    """
    try:
        # Read file content
        file_content = await file.read()

        # Forward to application layer
        async with httpx.AsyncClient(timeout=60.0) as client:
            files = {"file": (file.filename, file_content, file.content_type)}
            response = await client.post(
                f"{APP_LAYER_URL}/process",
                files=files
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=response.json().get("detail", "Unknown error")
                )

            return response.json()

    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail="Request timeout - document processing took too long"
        )
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to connect to application layer: {str(e)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@app.get("/api/v1/documents/{document_id}")
async def get_document(document_id: str):
    """
    Retrieve document by ID

    Args:
        document_id: Document ID

    Returns:
        Document data
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{APP_LAYER_URL}/document/{document_id}")

            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=response.json().get("detail", "Document not found")
                )

            return response.json()

    except httpx.RequestError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to connect to application layer: {str(e)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@app.delete("/api/v1/documents/{document_id}")
async def delete_document(document_id: str):
    """
    Delete document by ID

    Args:
        document_id: Document ID

    Returns:
        Success message
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.delete(f"{APP_LAYER_URL}/document/{document_id}")

            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=response.json().get("detail", "Document not found")
                )

            return response.json()

    except httpx.RequestError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to connect to application layer: {str(e)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Document Upload Service - API Layer",
        "version": "1.0.0",
        "description": "API Gateway for document upload microservice",
        "endpoints": {
            "health": "GET /health",
            "upload": "POST /api/v1/documents/upload",
            "get_document": "GET /api/v1/documents/{id}",
            "delete_document": "DELETE /api/v1/documents/{id}"
        }
    }
