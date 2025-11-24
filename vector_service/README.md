# Vector Service

A document vectorization microservice that handles semantic chunking, embedding generation, and hybrid search using Milvus and PostgreSQL.

## Architecture

```
                    +------------------+
                    |  Vector Service  |
                    |   (Port 8002)    |
                    +--------+---------+
                             |
     +-----------------------+-----------------------+
     |                       |                       |
+----v----+           +------v------+         +------v------+
|  Milvus |           |  PostgreSQL |         | Redis Queue |
| (19530) |           |    (5432)   |         |   (6379)    |
+---------+           +-------------+         +-------------+
     |
+----+----+
|         |
v         v
etcd    MinIO
```

## Features

- **Semantic Chunking**: Intelligent text splitting with overlap
- **Dense Embeddings**: Sentence-transformers (all-MiniLM-L6-v2)
- **Sparse Embeddings**: BM25-style keyword matching
- **Hybrid Search**: Combines dense and sparse for better results
- **Automatic Processing**: Listens to Redis queue for new documents

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/vectors/process` | Process document with provided data |
| `POST` | `/api/v1/vectors/process/{id}` | Fetch and process document by ID |
| `POST` | `/api/v1/vectors/search` | Search for relevant chunks |
| `GET` | `/api/v1/vectors/documents/{id}` | Get document info |
| `GET` | `/api/v1/vectors/documents/{id}/chunks` | Get all chunks for document |
| `DELETE` | `/api/v1/vectors/documents/{id}` | Delete document and chunks |
| `GET` | `/api/v1/vectors/stats` | Get vector store statistics |
| `GET` | `/health` | Health check endpoint |

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Shared network: `docker network create rag_shared_network`
- Redis running on the shared network

### Start the Service

```bash
cd vector_service
docker-compose up -d
```

### Search for Documents

```bash
curl -X POST "http://localhost:8002/api/v1/vectors/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "your search query",
    "top_k": 10,
    "search_type": "hybrid"
  }'
```

### Process Document by ID

```bash
curl -X POST "http://localhost:8002/api/v1/vectors/process/{document_id}"
```

## Search Types

| Type | Description | Use Case |
|------|-------------|----------|
| `dense` | Semantic similarity search | Conceptual queries |
| `sparse` | Keyword/BM25-style matching | Exact term queries |
| `hybrid` | Weighted combination | Best overall results |

### Hybrid Search Weights

```json
{
  "search_type": "hybrid",
  "dense_weight": 0.7,
  "sparse_weight": 0.3
}
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MILVUS_HOST` | `milvus-standalone` | Milvus server host |
| `MILVUS_PORT` | `19530` | Milvus port |
| `POSTGRES_HOST` | `vector-postgres` | PostgreSQL host |
| `POSTGRES_PORT` | `5432` | PostgreSQL port |
| `POSTGRES_USER` | `vectoruser` | Database user |
| `POSTGRES_PASSWORD` | `vectorpass` | Database password |
| `POSTGRES_DB` | `vector_metadata` | Database name |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Sentence-transformer model |
| `CHUNK_SIZE` | `512` | Maximum chunk size |
| `CHUNK_OVERLAP` | `50` | Overlap between chunks |
| `DOC_UPLOAD_SERVICE_URL` | `http://doc_upload_api:8080` | Doc upload service URL |
| `REDIS_HOST` | `rag-redis` | Redis host for queue |
| `REDIS_PORT` | `6379` | Redis port |

## Project Structure

```
vector_service/
├── app/
│   ├── main.py              # FastAPI app + lifespan
│   ├── config/              # Settings
│   ├── models/              # Pydantic models
│   ├── repositories/
│   │   ├── milvus_repository.py   # Vector storage
│   │   └── postgres_repository.py # Metadata storage
│   ├── services/
│   │   ├── vector_service.py      # Main orchestrator
│   │   ├── chunking_service.py    # Text chunking
│   │   ├── embedding_service.py   # Embeddings
│   │   └── doc_upload_client.py   # HTTP client
│   └── queue/
│       └── subscriber.py          # Redis worker
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── init_db.sql            # PostgreSQL schema
└── README.md
```

## Database Schemas

### Milvus Collection: `document_chunks`

| Field | Type | Description |
|-------|------|-------------|
| `chunk_id` | VARCHAR | Primary key |
| `document_id` | VARCHAR | Parent document ID |
| `dense_embedding` | FLOAT_VECTOR(384) | Dense embeddings |
| `sparse_embedding` | SPARSE_FLOAT_VECTOR | BM25 sparse vectors |
| `text` | VARCHAR | Chunk text content |

### PostgreSQL Table: `chunk_metadata`

| Column | Type | Description |
|--------|------|-------------|
| `chunk_id` | VARCHAR | Primary key |
| `document_id` | VARCHAR | Parent document ID |
| `filename` | VARCHAR | Original filename |
| `chunk_index` | INTEGER | Position in document |
| `char_start` | INTEGER | Start character position |
| `char_end` | INTEGER | End character position |
| `created_at` | TIMESTAMP | Creation timestamp |

## Background Worker

The service automatically starts a Redis queue worker that:
1. Listens on `document:process` queue
2. Receives document IDs from doc_upload service
3. Fetches document text from doc_upload API
4. Chunks, embeds, and stores the document
5. Logs processing results

## Scaling

Milvus and PostgreSQL can be scaled vertically by adjusting resource limits in `docker-compose.yml`. For horizontal scaling, consider Milvus cluster mode.

## Health Check

```bash
curl http://localhost:8002/health
```

Returns status of Milvus, PostgreSQL, and embedding model.
