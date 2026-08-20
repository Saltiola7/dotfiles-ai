BEGIN;

CREATE EXTENSION IF NOT EXISTS vector;
CREATE SCHEMA IF NOT EXISTS dks;

CREATE TABLE IF NOT EXISTS dks.schema_migrations (
    version integer PRIMARY KEY,
    applied_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS dks.projects (
    project_id text PRIMARY KEY,
    repository_remote text NOT NULL,
    object_format text NOT NULL DEFAULT 'sha1' CHECK (object_format = 'sha1'),
    active_revision_id text,
    active_run_id text,
    active_embedding_space_id text,
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS dks.project_roles (
    role_name name PRIMARY KEY,
    project_id text NOT NULL UNIQUE REFERENCES dks.projects(project_id) ON DELETE CASCADE
);

CREATE OR REPLACE FUNCTION dks.authorized_project()
RETURNS text
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = dks, pg_temp
AS $$
    SELECT project_id FROM dks.project_roles WHERE role_name = session_user
$$;
REVOKE ALL ON FUNCTION dks.authorized_project() FROM PUBLIC;

CREATE OR REPLACE FUNCTION dks.project_allowed(row_project_id text)
RETURNS boolean
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = dks, pg_temp
AS $$
    SELECT row_project_id = current_setting('dks.project_id', true)
       AND row_project_id = dks.authorized_project()
$$;
REVOKE ALL ON FUNCTION dks.project_allowed(text) FROM PUBLIC;

CREATE TABLE IF NOT EXISTS dks.embedding_spaces (
    project_id text NOT NULL REFERENCES dks.projects(project_id) ON DELETE CASCADE,
    embedding_space_id text NOT NULL,
    manifest_sha256 text NOT NULL CHECK (manifest_sha256 ~ '^[0-9a-f]{64}$'),
    dimensions integer NOT NULL CHECK (dimensions = 4096),
    PRIMARY KEY (project_id, embedding_space_id)
);

CREATE TABLE IF NOT EXISTS dks.source_revisions (
    project_id text NOT NULL REFERENCES dks.projects(project_id) ON DELETE CASCADE,
    revision_id text NOT NULL CHECK (revision_id ~ '^[0-9a-f]{40}$'),
    projected_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (project_id, revision_id)
);

CREATE TABLE IF NOT EXISTS dks.sync_runs (
    project_id text NOT NULL REFERENCES dks.projects(project_id) ON DELETE CASCADE,
    run_id text NOT NULL,
    revision_id text NOT NULL,
    state text NOT NULL CHECK (state IN ('staging', 'ready', 'active', 'retained', 'failed', 'abandoned')),
    expected_records integer NOT NULL DEFAULT 0 CHECK (expected_records >= 0),
    expected_chunks integer NOT NULL DEFAULT 0 CHECK (expected_chunks >= 0),
    expected_embeddings integer NOT NULL DEFAULT 0 CHECK (expected_embeddings >= 0),
    expected_nodes integer NOT NULL DEFAULT 0 CHECK (expected_nodes >= 0),
    expected_edges integer NOT NULL DEFAULT 0 CHECK (expected_edges >= 0),
    created_at timestamptz NOT NULL DEFAULT now(),
    finished_at timestamptz,
    PRIMARY KEY (project_id, run_id),
    UNIQUE (project_id, run_id, revision_id),
    FOREIGN KEY (project_id, revision_id)
        REFERENCES dks.source_revisions(project_id, revision_id) ON DELETE CASCADE
);
CREATE UNIQUE INDEX IF NOT EXISTS sync_runs_one_active
    ON dks.sync_runs(project_id) WHERE state = 'active';
ALTER TABLE dks.sync_runs ADD COLUMN IF NOT EXISTS expected_nodes integer NOT NULL DEFAULT 0
    CHECK (expected_nodes >= 0);

CREATE TABLE IF NOT EXISTS dks.content_objects (
    project_id text NOT NULL REFERENCES dks.projects(project_id) ON DELETE CASCADE,
    content_id text NOT NULL CHECK (content_id ~ '^[0-9a-f]{64}$'),
    body text NOT NULL,
    PRIMARY KEY (project_id, content_id)
);

CREATE TABLE IF NOT EXISTS dks.source_records (
    project_id text NOT NULL,
    revision_id text NOT NULL,
    path text NOT NULL CHECK (path !~ '(^|/)\.\.(/|$)'),
    blob_id text NOT NULL CHECK (blob_id ~ '^[0-9a-f]{40}$'),
    content_id text NOT NULL,
    PRIMARY KEY (project_id, revision_id, path),
    FOREIGN KEY (project_id, revision_id)
        REFERENCES dks.source_revisions(project_id, revision_id) ON DELETE CASCADE,
    FOREIGN KEY (project_id, content_id)
        REFERENCES dks.content_objects(project_id, content_id)
);

CREATE TABLE IF NOT EXISTS dks.knowledge_chunks (
    project_id text NOT NULL,
    chunk_id text NOT NULL CHECK (chunk_id ~ '^[0-9a-f]{64}$'),
    content_id text NOT NULL,
    chunker_version text NOT NULL CHECK (chunker_version = 'dks-markdown-v1'),
    ordinal integer NOT NULL CHECK (ordinal >= 0),
    start_byte integer NOT NULL CHECK (start_byte >= 0),
    end_byte integer NOT NULL CHECK (end_byte > start_byte),
    heading_path jsonb NOT NULL,
    heading_text text NOT NULL DEFAULT '',
    body text NOT NULL,
    body_sha256 text NOT NULL CHECK (body_sha256 ~ '^[0-9a-f]{64}$'),
    token_count integer NOT NULL CHECK (token_count BETWEEN 1 AND 1024),
    search_tsv tsvector GENERATED ALWAYS AS (
        setweight(to_tsvector('english', coalesce(heading_text, '')), 'A') ||
        setweight(to_tsvector('english', body), 'B')
    ) STORED,
    PRIMARY KEY (project_id, chunk_id),
    FOREIGN KEY (project_id, content_id)
        REFERENCES dks.content_objects(project_id, content_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS knowledge_chunks_fts
    ON dks.knowledge_chunks USING gin(search_tsv);

CREATE TABLE IF NOT EXISTS dks.embeddings (
    project_id text NOT NULL,
    embedding_id text NOT NULL CHECK (embedding_id ~ '^[0-9a-f]{64}$'),
    chunk_id text NOT NULL,
    embedding_space_id text NOT NULL,
    value vector(4096) NOT NULL,
    value_sha256 text NOT NULL CHECK (value_sha256 ~ '^[0-9a-f]{64}$'),
    PRIMARY KEY (project_id, embedding_id),
    UNIQUE (project_id, chunk_id, embedding_space_id),
    FOREIGN KEY (project_id, chunk_id)
        REFERENCES dks.knowledge_chunks(project_id, chunk_id) ON DELETE CASCADE,
    FOREIGN KEY (project_id, embedding_space_id)
        REFERENCES dks.embedding_spaces(project_id, embedding_space_id)
);

CREATE TABLE IF NOT EXISTS dks.revision_chunks (
    project_id text NOT NULL,
    run_id text NOT NULL,
    revision_id text NOT NULL,
    path text NOT NULL,
    chunk_id text NOT NULL,
    PRIMARY KEY (project_id, revision_id, path, chunk_id),
    FOREIGN KEY (project_id, run_id, revision_id)
        REFERENCES dks.sync_runs(project_id, run_id, revision_id) ON DELETE CASCADE,
    FOREIGN KEY (project_id, revision_id, path)
        REFERENCES dks.source_records(project_id, revision_id, path) ON DELETE CASCADE,
    FOREIGN KEY (project_id, chunk_id)
        REFERENCES dks.knowledge_chunks(project_id, chunk_id)
);

CREATE TABLE IF NOT EXISTS dks.graph_nodes (
    project_id text NOT NULL,
    node_id text NOT NULL CHECK (node_id ~ '^[0-9a-f]{64}$'),
    revision_id text NOT NULL,
    kind text NOT NULL CHECK (kind IN ('chunk', 'heading', 'path', 'ticket')),
    stable_key text NOT NULL,
    path text,
    heading_path jsonb,
    PRIMARY KEY (project_id, revision_id, node_id),
    FOREIGN KEY (project_id, revision_id)
        REFERENCES dks.source_revisions(project_id, revision_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS dks.graph_edges (
    project_id text NOT NULL,
    edge_id text NOT NULL CHECK (edge_id ~ '^[0-9a-f]{64}$'),
    run_id text NOT NULL,
    revision_id text NOT NULL,
    edge_type text NOT NULL CHECK (edge_type IN ('contains', 'links_to', 'depends_on', 'owns', 'reads')),
    source_node_id text NOT NULL,
    target_node_id text NOT NULL,
    source_start_byte integer NOT NULL CHECK (source_start_byte >= 0),
    source_end_byte integer NOT NULL CHECK (source_end_byte >= source_start_byte),
    PRIMARY KEY (project_id, edge_id),
    FOREIGN KEY (project_id, run_id, revision_id)
        REFERENCES dks.sync_runs(project_id, run_id, revision_id) ON DELETE CASCADE,
    FOREIGN KEY (project_id, revision_id, source_node_id)
        REFERENCES dks.graph_nodes(project_id, revision_id, node_id),
    FOREIGN KEY (project_id, revision_id, target_node_id)
        REFERENCES dks.graph_nodes(project_id, revision_id, node_id)
);

DO $constraints$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'projects_active_revision_fk'
                   AND conrelid = 'dks.projects'::regclass) THEN
        ALTER TABLE dks.projects ADD CONSTRAINT projects_active_revision_fk
            FOREIGN KEY (project_id, active_revision_id)
            REFERENCES dks.source_revisions(project_id, revision_id);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'projects_active_run_fk'
                   AND conrelid = 'dks.projects'::regclass) THEN
        ALTER TABLE dks.projects ADD CONSTRAINT projects_active_run_fk
            FOREIGN KEY (project_id, active_run_id)
            REFERENCES dks.sync_runs(project_id, run_id);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'projects_active_embedding_space_fk'
                   AND conrelid = 'dks.projects'::regclass) THEN
        ALTER TABLE dks.projects ADD CONSTRAINT projects_active_embedding_space_fk
            FOREIGN KEY (project_id, active_embedding_space_id)
            REFERENCES dks.embedding_spaces(project_id, embedding_space_id);
    END IF;
END
$constraints$;

DROP VIEW IF EXISTS dks.one_hop_graph;
DROP PROPERTY GRAPH IF EXISTS dks.knowledge_graph;

CREATE OR REPLACE VIEW dks.active_chunks WITH (security_invoker=true) AS
SELECT rc.project_id, rc.revision_id, rc.path, r.blob_id,
       c.chunk_id, c.content_id, c.ordinal, c.start_byte, c.end_byte,
       c.heading_path, c.heading_text, c.body, c.body_sha256, c.token_count,
       c.search_tsv, e.embedding_id, e.embedding_space_id, e.value
FROM dks.projects p
JOIN dks.revision_chunks rc
  ON rc.project_id = p.project_id AND rc.revision_id = p.active_revision_id
JOIN dks.source_records r
  ON r.project_id = rc.project_id AND r.revision_id = rc.revision_id AND r.path = rc.path
JOIN dks.knowledge_chunks c
  ON c.project_id = rc.project_id AND c.chunk_id = rc.chunk_id
JOIN dks.embeddings e
  ON e.project_id = c.project_id AND e.chunk_id = c.chunk_id
 AND e.embedding_space_id = p.active_embedding_space_id;

CREATE OR REPLACE VIEW dks.active_graph_nodes WITH (security_invoker=true) AS
SELECT n.* FROM dks.graph_nodes n
JOIN dks.projects p ON p.project_id = n.project_id AND p.active_revision_id = n.revision_id;

CREATE OR REPLACE VIEW dks.active_graph_edges WITH (security_invoker=true) AS
SELECT e.* FROM dks.graph_edges e
JOIN dks.projects p ON p.project_id = e.project_id AND p.active_revision_id = e.revision_id;

CREATE PROPERTY GRAPH dks.knowledge_graph
    VERTEX TABLES (
        dks.graph_nodes AS nodes KEY (project_id, revision_id, node_id)
        LABEL node PROPERTIES (project_id, node_id, revision_id, kind, stable_key, path, heading_path)
    )
    EDGE TABLES (
        dks.graph_edges AS edges KEY (project_id, edge_id)
        SOURCE KEY (project_id, revision_id, source_node_id) REFERENCES nodes (project_id, revision_id, node_id)
        DESTINATION KEY (project_id, revision_id, target_node_id) REFERENCES nodes (project_id, revision_id, node_id)
        LABEL asserted PROPERTIES (edge_id, edge_type, revision_id, source_start_byte, source_end_byte)
    );

CREATE OR REPLACE VIEW dks.one_hop_graph AS
SELECT * FROM GRAPH_TABLE (
    dks.knowledge_graph
    MATCH (source)-[edge]->(target)
    COLUMNS (
        source.project_id AS project_id,
        source.revision_id AS revision_id,
        source.node_id AS source_node_id,
        edge.edge_id AS edge_id,
        edge.edge_type AS edge_type,
        target.node_id AS target_node_id
    )
) graph_rows
JOIN dks.projects p USING (project_id)
WHERE graph_rows.revision_id = p.active_revision_id;

CREATE OR REPLACE FUNCTION dks.lexical_candidates(query_text text, candidate_limit integer DEFAULT 20)
RETURNS TABLE (project_id text, chunk_id text, score real)
LANGUAGE sql STABLE AS $$
    SELECT c.project_id, c.chunk_id,
           ts_rank_cd(c.search_tsv, websearch_to_tsquery('english', query_text), 32)
    FROM dks.active_chunks c
    WHERE c.search_tsv @@ websearch_to_tsquery('english', query_text)
    ORDER BY 3 DESC, c.chunk_id ASC
    LIMIT candidate_limit
$$;

CREATE OR REPLACE FUNCTION dks.vector_candidates(query_vector vector(4096), candidate_limit integer DEFAULT 20)
RETURNS TABLE (project_id text, chunk_id text, score double precision)
LANGUAGE sql STABLE AS $$
    SELECT c.project_id, c.chunk_id, -(c.value <#> query_vector)
    FROM dks.active_chunks c
    ORDER BY 3 DESC, c.chunk_id ASC
    LIMIT candidate_limit
$$;

ALTER TABLE dks.projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE dks.projects FORCE ROW LEVEL SECURITY;
ALTER TABLE dks.embedding_spaces ENABLE ROW LEVEL SECURITY;
ALTER TABLE dks.embedding_spaces FORCE ROW LEVEL SECURITY;
ALTER TABLE dks.source_revisions ENABLE ROW LEVEL SECURITY;
ALTER TABLE dks.source_revisions FORCE ROW LEVEL SECURITY;
ALTER TABLE dks.sync_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE dks.sync_runs FORCE ROW LEVEL SECURITY;
ALTER TABLE dks.content_objects ENABLE ROW LEVEL SECURITY;
ALTER TABLE dks.content_objects FORCE ROW LEVEL SECURITY;
ALTER TABLE dks.source_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE dks.source_records FORCE ROW LEVEL SECURITY;
ALTER TABLE dks.knowledge_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE dks.knowledge_chunks FORCE ROW LEVEL SECURITY;
ALTER TABLE dks.embeddings ENABLE ROW LEVEL SECURITY;
ALTER TABLE dks.embeddings FORCE ROW LEVEL SECURITY;
ALTER TABLE dks.revision_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE dks.revision_chunks FORCE ROW LEVEL SECURITY;
ALTER TABLE dks.graph_nodes ENABLE ROW LEVEL SECURITY;
ALTER TABLE dks.graph_nodes FORCE ROW LEVEL SECURITY;
ALTER TABLE dks.graph_edges ENABLE ROW LEVEL SECURITY;
ALTER TABLE dks.graph_edges FORCE ROW LEVEL SECURITY;

DO $policy$
DECLARE relation_name text;
BEGIN
    FOREACH relation_name IN ARRAY ARRAY[
        'projects', 'embedding_spaces', 'source_revisions', 'sync_runs',
        'content_objects', 'source_records', 'knowledge_chunks', 'embeddings',
        'revision_chunks', 'graph_nodes', 'graph_edges'
    ] LOOP
        EXECUTE format('DROP POLICY IF EXISTS project_isolation ON dks.%I', relation_name);
        EXECUTE format(
            'CREATE POLICY project_isolation ON dks.%I ' ||
            'USING (dks.project_allowed(project_id)) ' ||
            'WITH CHECK (dks.project_allowed(project_id))', relation_name);
    END LOOP;
END
$policy$;

INSERT INTO dks.schema_migrations(version) VALUES (1) ON CONFLICT DO NOTHING;

COMMIT;
