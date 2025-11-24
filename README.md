# Managed RAG System

A complete Retrieval-Augmented Generation (RAG) pipeline with automated document processing, vectorization, and semantic search capabilities. A document processing service to help students.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              RAG Pipeline                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                     │
│  │   Client    │───>│ doc_upload  │───>│   MongoDB   │                     │
│  │  (Upload)   │    │  (Port 8000)│    │ (Port 27017)│                     │
│  └─────────────┘    └──────┬──────┘    └─────────────┘                     │
│                            │                                                │
│                            │ Publish                                        │
│                            ▼                                                │
│                     ┌─────────────┐                                         │
│                     │    Redis    │                                         │
│                     │ (Port 6379) │                                         │
│                     └──────┬──────┘                                         │
│                            │                                                │
│                            │ Subscribe                                      │
│                            ▼                                                │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│  │   Client    │<───│vector_service│───>│   Milvus    │    │ PostgreSQL  │  │
│  │  (Search)   │    │  (Port 8002)│    │ (Port 19530)│    │ (Port 5432) │  │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Components

| Service | Port | Description |
|---------|------|-------------|
| **doc_upload** | 8000 | Document upload and text extraction |
| **vector_service** | 8002 | Vectorization and semantic search |
| **message_queue** | 6379 | Redis message broker |
| **MongoDB** | 27017 | Document storage |
| **PostgreSQL** | 5432 | Chunk metadata storage |
| **Milvus** | 19530 | Vector database |

## Data Flow

### 1. Document Upload (Automatic Processing)

```
Client → doc_upload → MongoDB → Redis Queue → vector_service → Milvus + PostgreSQL
```

1. **Upload**: Client uploads document to `doc_upload` service
2. **Extract**: Text is extracted (PDF, DOCX, XLSX, PPTX, TXT supported)
3. **Store**: Document stored in MongoDB with extracted text
4. **Queue**: Document ID published to Redis queue
5. **Process**: `vector_service` picks up message, fetches document
6. **Chunk**: Text split into semantic chunks with overlap
7. **Embed**: Dense (semantic) and sparse (keyword) embeddings generated
8. **Index**: Vectors stored in Milvus, metadata in PostgreSQL

### 2. Semantic Search

```
Client → vector_service → Milvus (vectors) + PostgreSQL (metadata) → Results
```

1. **Query**: Client sends search query
2. **Embed**: Query converted to embeddings
3. **Search**: Hybrid search (dense + sparse) in Milvus
4. **Retrieve**: Chunk text and metadata returned

## Quick Start

### Prerequisites

- Docker and Docker Compose
- ~8GB RAM (Milvus requires 4GB+)

### 1. Create Shared Network

```bash
docker network create rag_shared_network
```

### 2. Start Services (in order)

```bash
# 1. Start Redis message queue
cd message_queue
docker-compose up -d

# 2. Start document upload service
cd ../doc_upload
docker-compose up -d

# 3. Start vector service (includes Milvus + PostgreSQL)
cd ../vector_service
docker-compose up -d
```

### 3. Upload a Document

```bash
curl -X POST "http://localhost:8000/api/v1/documents/upload" \
  -F "file=@/path/to/document.pdf"
```

The document will be automatically processed and indexed.

### 4. Search Documents

```bash
curl -X POST "http://localhost:8002/api/v1/vectors/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is machine learning?",
    "top_k": 5,
    "search_type": "hybrid"
  }'
```

## API Reference

### Document Upload Service (Port 8000)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/documents/upload` | POST | Upload document |
| `/api/v1/documents/{id}` | GET | Get document |
| `/api/v1/documents/{id}` | DELETE | Delete document |
| `/health` | GET | Health check |

### Vector Service (Port 8002)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/vectors/search` | POST | Search documents |
| `/api/v1/vectors/process/{id}` | POST | Manual process |
| `/api/v1/vectors/documents/{id}` | GET | Get document info |
| `/api/v1/vectors/documents/{id}/chunks` | GET | Get chunks |
| `/api/v1/vectors/documents/{id}` | DELETE | Delete document |
| `/health` | GET | Health check |

## Search Types

| Type | Description | Best For |
|------|-------------|----------|
| `dense` | Semantic similarity | Conceptual questions |
| `sparse` | Keyword matching | Specific terms |
| `hybrid` | Combined (default) | General queries |

## Project Structure

```
managed_rag/
├── doc_upload/           # Document upload service
│   ├── api_layer/       # API gateway
│   ├── app_layer/       # Business logic
│   ├── nginx/           # Load balancer
│   ├── docker-compose.yml
│   └── README.md
│
├── vector_service/       # Vectorization service
│   ├── app/             # FastAPI application
│   ├── docker-compose.yml
│   ├── init_db.sql      # PostgreSQL schema
│   └── README.md
│
├── message_queue/        # Redis message broker
│   ├── docker-compose.yml
│   └── README.md
│
└── README.md            # This file
```

## Configuration

### Environment Variables

See individual service READMEs for complete configuration options.

Key settings:

| Variable | Service | Description |
|----------|---------|-------------|
| `CHUNK_SIZE` | vector_service | Max chunk size (default: 512) |
| `CHUNK_OVERLAP` | vector_service | Overlap between chunks (default: 50) |
| `EMBEDDING_MODEL` | vector_service | Sentence-transformer model |

## Monitoring

### Health Checks

```bash
# Document upload service
curl http://localhost:8000/health

# Vector service
curl http://localhost:8002/health
```

### Container Status

```bash
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

### View Logs

```bash
# Document upload
docker logs -f doc_upload_api

# Vector service
docker logs -f vector-service
```

## Admin UIs

| Service | URL | Description |
|---------|-----|-------------|
| Milvus | http://localhost:9091 | Milvus metrics |
| MinIO | http://localhost:9001 | Object storage UI |
| pgAdmin | Configure separately | PostgreSQL admin |
| Mongo Express | Configure separately | MongoDB admin |

## Scaling

### Horizontal Scaling

- **doc_upload**: Add app instances in docker-compose, update nginx upstream
- **vector_service**: Single instance (scale Milvus/PostgreSQL instead)

### Vertical Scaling

Adjust resource limits in `docker-compose.yml`:

```yaml
deploy:
  resources:
    limits:
      cpus: '4'
      memory: 4G
```

## Troubleshooting

### Common Issues

1. **Milvus not starting**: Ensure 4GB+ RAM available
2. **Network connectivity**: Verify all services on `rag_shared_network`
3. **Redis connection**: Check Redis is running before other services

### Reset Everything

```bash
# Stop all services
cd doc_upload && docker-compose down -v
cd ../vector_service && docker-compose down -v
cd ../message_queue && docker-compose down -v

# Remove network
docker network rm rag_shared_network

# Start fresh
docker network create rag_shared_network
```

## Technology Stack

- **FastAPI**: Web framework
- **MongoDB**: Document storage
- **Milvus**: Vector database
- **PostgreSQL**: Metadata storage
- **Redis**: Message queue
- **Sentence-Transformers**: Embeddings
- **Docker**: Containerization
- **Nginx**: Load balancing
