-- Initialize vector metadata database

-- Create chunks metadata table
CREATE TABLE IF NOT EXISTS chunk_metadata (
    id UUID PRIMARY KEY,
    document_id UUID NOT NULL,
    chunk_index INTEGER NOT NULL,
    filename VARCHAR(500) NOT NULL,
    file_format VARCHAR(50) NOT NULL,
    file_size BIGINT,
    upload_timestamp TIMESTAMPTZ NOT NULL,
    chunk_start_char INTEGER,
    chunk_end_char INTEGER,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    -- Index for faster lookups by document_id
    CONSTRAINT unique_document_chunk UNIQUE (document_id, chunk_index)
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_chunk_document_id ON chunk_metadata(document_id);
CREATE INDEX IF NOT EXISTS idx_chunk_filename ON chunk_metadata(filename);
CREATE INDEX IF NOT EXISTS idx_chunk_file_format ON chunk_metadata(file_format);
CREATE INDEX IF NOT EXISTS idx_chunk_upload_timestamp ON chunk_metadata(upload_timestamp);
CREATE INDEX IF NOT EXISTS idx_chunk_metadata ON chunk_metadata USING GIN (metadata);

-- Create documents summary table for quick lookups
CREATE TABLE IF NOT EXISTS document_summary (
    document_id UUID PRIMARY KEY,
    filename VARCHAR(500) NOT NULL,
    file_format VARCHAR(50) NOT NULL,
    file_size BIGINT,
    total_chunks INTEGER NOT NULL,
    upload_timestamp TIMESTAMPTZ NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_doc_summary_filename ON document_summary(filename);
CREATE INDEX IF NOT EXISTS idx_doc_summary_upload ON document_summary(upload_timestamp);
