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
    chunker_version text NOT NULL CHECK (chunker_version IN ('dks-markdown-v1','dks-source-v1')),
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
ALTER TABLE dks.knowledge_chunks DROP CONSTRAINT IF EXISTS knowledge_chunks_chunker_version_check;
ALTER TABLE dks.knowledge_chunks ADD CONSTRAINT knowledge_chunks_chunker_version_check
    CHECK (chunker_version IN ('dks-markdown-v1','dks-source-v1'));

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

CREATE TABLE IF NOT EXISTS dks.authority_snapshots (
    project_id text NOT NULL REFERENCES dks.projects(project_id) ON DELETE CASCADE,
    source_kind text NOT NULL,
    snapshot_id text NOT NULL CHECK (snapshot_id ~ '^[0-9a-f]{64}$'),
    manifest_sha256 text NOT NULL CHECK (manifest_sha256 ~ '^[0-9a-f]{64}$'),
    privacy_sequence numeric(20,0) NOT NULL CHECK (privacy_sequence >= 0),
    privacy_digest text NOT NULL CHECK (privacy_digest ~ '^[0-9a-f]{64}$'),
    state text NOT NULL CHECK (state IN ('staging','active','retained','failed')),
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (project_id, source_kind, snapshot_id)
);
CREATE UNIQUE INDEX IF NOT EXISTS authority_snapshots_one_active
    ON dks.authority_snapshots(project_id, source_kind) WHERE state = 'active';

CREATE TABLE IF NOT EXISTS dks.privacy_state (
    project_id text PRIMARY KEY REFERENCES dks.projects(project_id) ON DELETE CASCADE,
    privacy_sequence numeric(20,0) NOT NULL CHECK (privacy_sequence >= 0),
    privacy_digest text NOT NULL CHECK (privacy_digest ~ '^[0-9a-f]{64}$'),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS dks.privacy_denies (
    project_id text NOT NULL REFERENCES dks.projects(project_id) ON DELETE CASCADE,
    source_kind text NOT NULL,
    record_id text NOT NULL CHECK (record_id ~ '^[0-9a-f]{64}$'),
    reason text NOT NULL CHECK (reason IN ('deleted','expired','forgotten')),
    denied_at numeric(20,0) NOT NULL CHECK (denied_at >= 0),
    PRIMARY KEY (project_id, source_kind, record_id)
);

CREATE TABLE IF NOT EXISTS dks.authority_records (
    project_id text NOT NULL,
    source_kind text NOT NULL,
    snapshot_id text NOT NULL,
    record_id text NOT NULL CHECK (record_id ~ '^[0-9a-f]{64}$'),
    revision text NOT NULL CHECK (revision ~ '^[0-9a-f]{64}$'),
    retention text NOT NULL CHECK (retention IN ('retained','expires','tombstoned')),
    body text NOT NULL,
    content_id text NOT NULL CHECK (content_id ~ '^[0-9a-f]{64}$'),
    PRIMARY KEY (project_id, source_kind, snapshot_id, record_id),
    FOREIGN KEY (project_id, source_kind, snapshot_id)
        REFERENCES dks.authority_snapshots(project_id, source_kind, snapshot_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS dks.authority_chunks (
    project_id text NOT NULL,
    source_kind text NOT NULL,
    snapshot_id text NOT NULL,
    record_id text NOT NULL,
    chunk_id text NOT NULL CHECK (chunk_id ~ '^[0-9a-f]{64}$'),
    ordinal integer NOT NULL CHECK (ordinal >= 0),
    start_byte integer NOT NULL CHECK (start_byte >= 0),
    end_byte integer NOT NULL CHECK (end_byte > start_byte),
    body text NOT NULL,
    body_sha256 text NOT NULL CHECK (body_sha256 ~ '^[0-9a-f]{64}$'),
    token_count integer NOT NULL CHECK (token_count BETWEEN 1 AND 1024),
    search_tsv tsvector GENERATED ALWAYS AS (to_tsvector('english', body)) STORED,
    PRIMARY KEY (project_id, source_kind, snapshot_id, record_id, chunk_id),
    FOREIGN KEY (project_id, source_kind, snapshot_id, record_id)
        REFERENCES dks.authority_records(project_id, source_kind, snapshot_id, record_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS authority_chunks_fts ON dks.authority_chunks USING gin(search_tsv);

CREATE TABLE IF NOT EXISTS dks.authority_embeddings (
    project_id text NOT NULL,
    source_kind text NOT NULL,
    snapshot_id text NOT NULL,
    record_id text NOT NULL,
    chunk_id text NOT NULL,
    embedding_space_id text NOT NULL,
    value vector(4096) NOT NULL,
    value_sha256 text NOT NULL CHECK (value_sha256 ~ '^[0-9a-f]{64}$'),
    PRIMARY KEY (project_id, source_kind, snapshot_id, record_id, chunk_id, embedding_space_id),
    FOREIGN KEY (project_id, source_kind, snapshot_id, record_id, chunk_id)
        REFERENCES dks.authority_chunks(project_id, source_kind, snapshot_id, record_id, chunk_id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS dks.code_embeddings (
    project_id text NOT NULL,
    chunk_id text NOT NULL,
    embedding_space_id text NOT NULL,
    value vector(3584) NOT NULL,
    value_sha256 text NOT NULL CHECK (value_sha256 ~ '^[0-9a-f]{64}$'),
    PRIMARY KEY (project_id, chunk_id, embedding_space_id),
    FOREIGN KEY (project_id, chunk_id) REFERENCES dks.knowledge_chunks(project_id, chunk_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS dks.code_embedding_spaces (
    project_id text NOT NULL REFERENCES dks.projects(project_id) ON DELETE CASCADE,
    embedding_space_id text NOT NULL,
    manifest_sha256 text NOT NULL CHECK (manifest_sha256 ~ '^[0-9a-f]{64}$'),
    dimensions integer NOT NULL CHECK (dimensions = 3584),
    PRIMARY KEY (project_id, embedding_space_id)
);
ALTER TABLE dks.code_embeddings DROP CONSTRAINT IF EXISTS code_embeddings_space_fk;
ALTER TABLE dks.code_embeddings ADD CONSTRAINT code_embeddings_space_fk
    FOREIGN KEY (project_id, embedding_space_id)
    REFERENCES dks.code_embedding_spaces(project_id, embedding_space_id);

CREATE TABLE IF NOT EXISTS dks.graph_imports (
    project_id text NOT NULL REFERENCES dks.projects(project_id) ON DELETE CASCADE,
    revision_id text NOT NULL,
    artifact_sha256 text NOT NULL CHECK (artifact_sha256 ~ '^[0-9a-f]{64}$'),
    normalized_sha256 text NOT NULL CHECK (normalized_sha256 ~ '^[0-9a-f]{64}$'),
    extractor_version text NOT NULL,
    extractor_revision text NOT NULL CHECK (extractor_revision ~ '^[0-9a-f]{40}$'),
    config_sha256 text NOT NULL CHECK (config_sha256 ~ '^[0-9a-f]{64}$'),
    source_profile_sha256 text NOT NULL CHECK (source_profile_sha256 ~ '^[0-9a-f]{64}$'),
    corpus_manifest_sha256 text NOT NULL CHECK (corpus_manifest_sha256 ~ '^[0-9a-f]{64}$'),
    execution_receipt_sha256 text NOT NULL CHECK (execution_receipt_sha256 ~ '^[0-9a-f]{64}$'),
    runtime_sha256 text NOT NULL CHECK (runtime_sha256 ~ '^[0-9a-f]{64}$'),
    producer_sha256 text NOT NULL CHECK (producer_sha256 ~ '^[0-9a-f]{64}$'),
    expected_nodes integer NOT NULL CHECK (expected_nodes >= 0),
    expected_edges integer NOT NULL CHECK (expected_edges >= 0),
    excluded_external_nodes integer NOT NULL CHECK (excluded_external_nodes >= 0),
    excluded_dangling_edges integer NOT NULL CHECK (excluded_dangling_edges >= 0),
    state text NOT NULL CHECK (state IN ('staging','active','retained','failed')),
    PRIMARY KEY (project_id, artifact_sha256)
);
CREATE UNIQUE INDEX IF NOT EXISTS graph_imports_one_active
    ON dks.graph_imports(project_id) WHERE state = 'active';
ALTER TABLE dks.graph_imports ADD COLUMN IF NOT EXISTS corpus_manifest_sha256 text
    CHECK (corpus_manifest_sha256 ~ '^[0-9a-f]{64}$');
ALTER TABLE dks.graph_imports ADD COLUMN IF NOT EXISTS execution_receipt_sha256 text
    CHECK (execution_receipt_sha256 ~ '^[0-9a-f]{64}$');
ALTER TABLE dks.graph_imports ADD COLUMN IF NOT EXISTS runtime_sha256 text
    DEFAULT '71cb98287d1e526a8f8be9f60d10462de2df8c547bb1c5bfca2376e07a056be8'
    CHECK (runtime_sha256 ~ '^[0-9a-f]{64}$');
ALTER TABLE dks.graph_imports ADD COLUMN IF NOT EXISTS producer_sha256 text
    DEFAULT '7e23d864064906146e20e1c99d343e9bbb22abb5b3f8c913092ed440f2533091'
    CHECK (producer_sha256 ~ '^[0-9a-f]{64}$');
ALTER TABLE dks.graph_imports ALTER COLUMN runtime_sha256 SET NOT NULL;
ALTER TABLE dks.graph_imports ALTER COLUMN producer_sha256 SET NOT NULL;

CREATE TABLE IF NOT EXISTS dks.imported_graph_nodes (
    project_id text NOT NULL,
    artifact_sha256 text NOT NULL,
    node_id text NOT NULL CHECK (node_id ~ '^[0-9a-f]{64}$'),
    raw_id text NOT NULL,
    label text NOT NULL,
    confidence text NOT NULL CHECK (confidence IN ('EXTRACTED','INFERRED','AMBIGUOUS')),
    source_path text NOT NULL,
    source_start_byte integer NOT NULL,
    source_end_byte integer NOT NULL,
    PRIMARY KEY (project_id, artifact_sha256, node_id),
    FOREIGN KEY (project_id, artifact_sha256) REFERENCES dks.graph_imports(project_id, artifact_sha256) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS dks.imported_graph_edges (
    project_id text NOT NULL,
    artifact_sha256 text NOT NULL,
    edge_id text NOT NULL CHECK (edge_id ~ '^[0-9a-f]{64}$'),
    source_node_id text NOT NULL,
    target_node_id text NOT NULL,
    relation text NOT NULL,
    confidence text NOT NULL CHECK (confidence IN ('EXTRACTED','INFERRED','AMBIGUOUS')),
    source_path text NOT NULL,
    source_start_byte integer NOT NULL CHECK (source_start_byte >= 0),
    source_end_byte integer NOT NULL CHECK (source_end_byte > source_start_byte),
    PRIMARY KEY (project_id, artifact_sha256, edge_id),
    FOREIGN KEY (project_id, artifact_sha256, source_node_id)
        REFERENCES dks.imported_graph_nodes(project_id, artifact_sha256, node_id),
    FOREIGN KEY (project_id, artifact_sha256, target_node_id)
        REFERENCES dks.imported_graph_nodes(project_id, artifact_sha256, node_id)
);

CREATE TABLE IF NOT EXISTS dks.imported_graph_node_chunks (
    project_id text NOT NULL,
    artifact_sha256 text NOT NULL,
    node_id text NOT NULL,
    chunk_id text NOT NULL,
    overlap_start_byte integer NOT NULL,
    overlap_end_byte integer NOT NULL,
    PRIMARY KEY (project_id,artifact_sha256,node_id,chunk_id),
    FOREIGN KEY (project_id,artifact_sha256,node_id)
        REFERENCES dks.imported_graph_nodes(project_id,artifact_sha256,node_id) ON DELETE CASCADE,
    FOREIGN KEY (project_id,chunk_id)
        REFERENCES dks.knowledge_chunks(project_id,chunk_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS dks.ranking_policies (
    project_id text NOT NULL REFERENCES dks.projects(project_id) ON DELETE CASCADE,
    activation_id text NOT NULL,
    policy_id text NOT NULL CHECK (policy_id IN ('dks-rrf-v1','dks-quality-v2')),
    manifest_sha256 text NOT NULL CHECK (manifest_sha256 ~ '^[0-9a-f]{64}$'),
    benchmark_sha256 text CHECK (benchmark_sha256 ~ '^[0-9a-f]{64}$'),
    benchmark_aggregate_sha256 text CHECK (benchmark_aggregate_sha256 ~ '^[0-9a-f]{64}$'),
    source_revision_id text CHECK (source_revision_id ~ '^[0-9a-f]{40}$'),
    source_projection_sha256 text CHECK (source_projection_sha256 ~ '^[0-9a-f]{64}$'),
    authority_snapshot_set_sha256 text CHECK (authority_snapshot_set_sha256 ~ '^[0-9a-f]{64}$'),
    authority_projection_sha256 text CHECK (authority_projection_sha256 ~ '^[0-9a-f]{64}$'),
    privacy_sequence numeric(20,0) CHECK (privacy_sequence >= 0),
    privacy_digest text CHECK (privacy_digest ~ '^[0-9a-f]{64}$'),
    code_embedding_space_id text,
    graph_artifact_sha256 text,
    reranker_manifest_sha256 text CHECK (reranker_manifest_sha256 ~ '^[0-9a-f]{64}$'),
    active boolean NOT NULL DEFAULT false,
    activated_at timestamptz,
    PRIMARY KEY (project_id, activation_id),
    FOREIGN KEY (project_id, code_embedding_space_id)
        REFERENCES dks.code_embedding_spaces(project_id, embedding_space_id)
);
CREATE UNIQUE INDEX IF NOT EXISTS ranking_policies_one_active
    ON dks.ranking_policies(project_id) WHERE active;
ALTER TABLE dks.ranking_policies ADD COLUMN IF NOT EXISTS source_revision_id text
    CHECK (source_revision_id ~ '^[0-9a-f]{40}$');
ALTER TABLE dks.ranking_policies ADD COLUMN IF NOT EXISTS source_projection_sha256 text
    CHECK (source_projection_sha256 ~ '^[0-9a-f]{64}$');
ALTER TABLE dks.ranking_policies ADD COLUMN IF NOT EXISTS authority_snapshot_set_sha256 text
    CHECK (authority_snapshot_set_sha256 ~ '^[0-9a-f]{64}$');
ALTER TABLE dks.ranking_policies ADD COLUMN IF NOT EXISTS authority_projection_sha256 text
    CHECK (authority_projection_sha256 ~ '^[0-9a-f]{64}$');
ALTER TABLE dks.ranking_policies ADD COLUMN IF NOT EXISTS privacy_sequence numeric(20,0)
    CHECK (privacy_sequence >= 0);
ALTER TABLE dks.ranking_policies ADD COLUMN IF NOT EXISTS privacy_digest text
    CHECK (privacy_digest ~ '^[0-9a-f]{64}$');

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

DO $policy$
DECLARE relation_name text;
BEGIN
    FOREACH relation_name IN ARRAY ARRAY[
        'projects', 'embedding_spaces', 'source_revisions', 'sync_runs',
        'content_objects', 'source_records', 'knowledge_chunks', 'embeddings',
        'revision_chunks', 'graph_nodes', 'graph_edges', 'authority_snapshots', 'privacy_state',
        'privacy_denies',
        'authority_records', 'authority_chunks', 'authority_embeddings',
        'code_embedding_spaces', 'code_embeddings', 'graph_imports', 'imported_graph_nodes',
        'imported_graph_edges', 'imported_graph_node_chunks', 'ranking_policies'
    ] LOOP
        EXECUTE format('ALTER TABLE dks.%I ENABLE ROW LEVEL SECURITY', relation_name);
        EXECUTE format('ALTER TABLE dks.%I FORCE ROW LEVEL SECURITY', relation_name);
        EXECUTE format('DROP POLICY IF EXISTS project_isolation ON dks.%I', relation_name);
        EXECUTE format(
            'CREATE POLICY project_isolation ON dks.%I ' ||
            'USING (dks.project_allowed(project_id)) ' ||
            'WITH CHECK (dks.project_allowed(project_id))', relation_name);
    END LOOP;
END
$policy$;

INSERT INTO dks.schema_migrations(version) VALUES (1) ON CONFLICT DO NOTHING;
INSERT INTO dks.schema_migrations(version) VALUES (2) ON CONFLICT DO NOTHING;
INSERT INTO dks.schema_migrations(version) VALUES (3) ON CONFLICT DO NOTHING;
INSERT INTO dks.schema_migrations(version) VALUES (5) ON CONFLICT DO NOTHING;

COMMIT;
