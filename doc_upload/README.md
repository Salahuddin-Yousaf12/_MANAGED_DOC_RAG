# Document Upload Service

A scalable document upload and text extraction microservice built with FastAPI, MongoDB, and Nginx load balancing.

## Architecture

```
                    +------------------+
                    |   API Gateway    |
                    |   (Port 8000)    |
                    +--------+---------+
                             |
                    +--------v---------+
                    |      Nginx       |
                    |  Load Balancer   |
                    |   (Port 8001)    |
                    +--------+---------+
                             |
              +--------------+--------------+
              |                             |
     +--------v--------+           +--------v--------+
     |      App 1      |           |      App 2      |
     |   (FastAPI)     |           |   (FastAPI)     |
     +--------+--------+           +--------+--------+
              |                             |
              +--------------+--------------+
                             |
                    +--------v---------+
                    |     MongoDB      |
                    |  (Port 27017)    |
                    +------------------+
                             |
                    +--------v---------+
                    |   Redis Queue    |
                    | (rag_shared_net) |
                    +------------------+
```

## Components

### API Layer (`api_layer/`)
- External-facing FastAPI gateway
- Handles client requests and forwards to app layer
- Exposes port 8000

### Application Layer (`app_layer/`)
- Core business logic
- Document text extraction (PDF, DOCX, TXT, XLSX, PPTX)
- MongoDB storage
- Redis queue publishing for vector processing

### Nginx (`nginx/`)
- Load balances across app instances
- Provides horizontal scaling capability

## Supported File Formats

| Format | Extension | Extractor |
|--------|-----------|-----------|
| PDF | `.pdf` | PyPDF2 |
| Word | `.docx` | python-docx |
| Excel | `.xlsx` | openpyxl |
| PowerPoint | `.pptx` | python-pptx |
| Text | `.txt` | Native |

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/documents/upload` | Upload and process a document |
| `GET` | `/api/v1/documents/{id}` | Retrieve document by ID |
| `DELETE` | `/api/v1/documents/{id}` | Delete document by ID |
| `GET` | `/health` | Health check endpoint |

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Shared network: `docker network create rag_shared_network`

### Start the Service

```bash
cd doc_upload
docker-compose up -d
```

### Upload a Document

```bash
curl -X POST "http://localhost:8000/api/v1/documents/upload" \
  -F "file=@/path/to/document.pdf"
```

### Get a Document

```bash
curl "http://localhost:8000/api/v1/documents/{document_id}"
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MONGODB_URL` | `mongodb://mongodb:27017` | MongoDB connection URL |
| `MONGODB_DB_NAME` | `document_store` | Database name |
| `MONGODB_COLLECTION` | `documents` | Collection name |
| `REDIS_HOST` | `rag-redis` | Redis host for queue |
| `REDIS_PORT` | `6379` | Redis port |

## Project Structure

```
doc_upload/
├── api_layer/              # API Gateway
│   ├── main.py            # FastAPI app
│   ├── requirements.txt
│   └── Dockerfile
├── app_layer/              # Application Layer
│   ├── main.py            # FastAPI app
│   ├── config/            # Settings
│   ├── models/            # Pydantic models
│   ├── repositories/      # MongoDB repository
│   ├── services/          # Business logic
│   │   └── extractors/    # Text extractors
│   ├── queue/             # Redis publisher
│   ├── requirements.txt
│   └── Dockerfile
├── nginx/
│   └── nginx.conf         # Load balancer config
├── docker-compose.yml
└── README.md
```

## Integration with Vector Service

When a document is uploaded:
1. Text is extracted and stored in MongoDB
2. A message is published to Redis queue (`document:process`)
3. Vector Service picks up the message and processes the document
4. Chunks and embeddings are stored in Milvus + PostgreSQL

## Scaling

To add more app instances, add services in `docker-compose.yml` and update `nginx.conf` upstream configuration.

## Health Check

```bash
curl http://localhost:8000/health
```

Returns status of API layer and downstream app layer.
