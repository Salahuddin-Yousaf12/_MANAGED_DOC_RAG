"""
Document repository for MongoDB operations
"""
from typing import Optional, Dict, Any
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection
from config.settings import settings
from models.document import Document


class DocumentRepository:
    """Repository for document CRUD operations in MongoDB"""

    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.db: Optional[AsyncIOMotorDatabase] = None
        self.collection: Optional[AsyncIOMotorCollection] = None

    async def connect(self):
        """Establish connection to MongoDB"""
        try:
            self.client = AsyncIOMotorClient(settings.MONGODB_URL)
            self.db = self.client[settings.MONGODB_DB_NAME]
            self.collection = self.db[settings.MONGODB_COLLECTION]

            # Test connection
            await self.client.admin.command('ping')
            print(f"✓ Connected to MongoDB at {settings.MONGODB_URL}")
        except Exception as e:
            print(f"✗ Failed to connect to MongoDB: {str(e)}")
            raise

    async def disconnect(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            print("✓ MongoDB connection closed")

    async def create_document(self, document: Document) -> str:
        """
        Insert a new document into MongoDB

        Args:
            document: Document model instance

        Returns:
            Document ID

        Raises:
            Exception: If insertion fails
        """
        try:
            doc_dict = document.model_dump()
            # Use 'id' as '_id' for MongoDB
            doc_dict['_id'] = doc_dict.pop('id')

            result = await self.collection.insert_one(doc_dict)
            return str(result.inserted_id)
        except Exception as e:
            raise Exception(f"Failed to insert document: {str(e)}")

    async def get_document_by_id(self, document_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a document by ID

        Args:
            document_id: Document ID

        Returns:
            Document dict or None if not found
        """
        try:
            doc = await self.collection.find_one({"_id": document_id})
            if doc:
                doc['id'] = doc.pop('_id')
            return doc
        except Exception as e:
            raise Exception(f"Failed to retrieve document: {str(e)}")

    async def delete_document(self, document_id: str) -> bool:
        """
        Delete a document by ID

        Args:
            document_id: Document ID

        Returns:
            True if deleted, False if not found
        """
        try:
            result = await self.collection.delete_one({"_id": document_id})
            return result.deleted_count > 0
        except Exception as e:
            raise Exception(f"Failed to delete document: {str(e)}")

    async def count_documents(self) -> int:
        """
        Count total documents in collection

        Returns:
            Number of documents
        """
        try:
            return await self.collection.count_documents({})
        except Exception as e:
            raise Exception(f"Failed to count documents: {str(e)}")


# Global repository instance
document_repository = DocumentRepository()
