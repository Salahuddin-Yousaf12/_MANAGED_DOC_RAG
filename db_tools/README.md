# Database UI Tools

UI tools for viewing PostgreSQL and Milvus databases.

## Prerequisites

Start the other services first (they create the networks):

```bash
# 1. Start doc_upload (creates rag_shared_network)
cd ../doc_upload
docker-compose up -d

# 2. Start vector_service (creates vector_service_vector_network)
cd ../vector_service
docker-compose up -d

# 3. Then start db_tools
cd ../db_tools
docker-compose up -d
```

## Tools

### pgAdmin (PostgreSQL)

- **URL:** http://localhost:5050
- **Login:**
  - Email: `admin@admin.com`
  - Password: `admin`

**To connect to PostgreSQL:**
1. Right-click "Servers" → "Register" → "Server"
2. General tab: Name it anything (e.g., "Vector DB")
3. Connection tab:
   - Host: `vector-postgres`
   - Port: `5432`
   - Database: `vector_metadata`
   - Username: `vectoruser`
   - Password: `vectorpass`

### Attu (Milvus)

- **URL:** http://localhost:3000
- Auto-connects to Milvus at `milvus-standalone:19530`

## Ports Summary

| Tool | Port | URL |
|------|------|-----|
| pgAdmin | 5050 | http://localhost:5050 |
| Attu | 3000 | http://localhost:3000 |
