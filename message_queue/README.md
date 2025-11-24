# Message Queue - Redis

Event-driven communication between microservices using Redis.

## Architecture

```
┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐
│   doc_upload    │         │      Redis      │         │ vector_service  │
│                 │         │                 │         │                 │
│  1. Store in    │         │                 │         │                 │
│     MongoDB     │         │                 │         │                 │
│                 │         │                 │         │                 │
│  2. Publish ────┼────────>│  document:      │         │                 │
│     message     │         │  process queue  │────────>│  3. Receive     │
│                 │         │                 │         │     message     │
│                 │         │                 │         │                 │
│                 │         │                 │         │  4. Fetch doc   │
│                 │<────────┼─────────────────┼─────────┤     from        │
│                 │         │                 │         │     doc_upload  │
│                 │         │                 │         │                 │
│                 │         │                 │         │  5. Process &   │
│                 │         │                 │         │     store in    │
│                 │         │                 │         │     Milvus/PG   │
└─────────────────┘         └─────────────────┘         └─────────────────┘
```

## Quick Start

```bash
cd message_queue
docker-compose up -d
```

## Files

| File | Description |
|------|-------------|
| `docker-compose.yml` | Redis container configuration |
| `publisher.py` | Publisher module (used by doc_upload) |
| `subscriber.py` | Subscriber/worker module (used by vector_service) |
| `queue_config.py` | Shared configuration reference |

## Message Format

```json
{
    "document_id": "8f322715-6d94-445d-8c4d-7e382eec71f7",
    "filename": "example.pdf",
    "timestamp": "2024-01-01T12:00:00Z"
}
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| REDIS_HOST | rag-redis | Redis hostname |
| REDIS_PORT | 6379 | Redis port |
| REDIS_DB | 0 | Redis database number |
