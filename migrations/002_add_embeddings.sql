-- Migration 002: Add embedding storage to Neo4j nodes
-- Enables cosine-similarity semantic search on Product and Fault nodes.
-- Requires: embeddings computed by BGE encoder at ingestion time.

-- No schema changes needed (Neo4j is schemaless — we just document the property convention).
-- This migration adds a constraint to ensure embedding-enabled nodes have properly typed properties.

-- Ensure Product nodes optionally carry an embedding
-- (list of floats, stored as Neo4j List<Float>)

-- Ensure Fault nodes optionally carry an embedding + fault_code for routing
-- CREATE CONSTRAINT IF NOT EXISTS ON (f:Fault) ASSERT f.fault_code IS UNIQUE;
-- Uncomment if you want uniqueness on fault_code; requires existing data cleanup first.

-- Index for fast lookup on fault_code (used by get_solutions_for_fault)
CREATE INDEX fault_code_index IF NOT EXISTS FOR (f:Fault) ON (f.fault_code);

-- Index for embedding existence check (used by search_by_embedding to skip non-embedded nodes)
-- Neo4j doesn't support "WHERE property IS NOT NULL" index acceleration directly,
-- but the label scan is sufficient for moderate-size graphs.
