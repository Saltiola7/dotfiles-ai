BEGIN;

CREATE SCHEMA IF NOT EXISTS context;

CREATE TABLE IF NOT EXISTS context.schema_migrations (
    version integer PRIMARY KEY,
    applied_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS context.tickets (
    id text PRIMARY KEY,
    context text NOT NULL,
    title text NOT NULL,
    state text NOT NULL,
    priority text NOT NULL,
    points numeric,
    source_commit text NOT NULL,
    source_blob text NOT NULL,
    payload jsonb NOT NULL,
    projected_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS context.ticket_relations (
    source_id text NOT NULL REFERENCES context.tickets(id) ON DELETE CASCADE,
    target_id text NOT NULL REFERENCES context.tickets(id) ON DELETE CASCADE,
    relation_type text NOT NULL,
    metadata jsonb NOT NULL DEFAULT '{}',
    PRIMARY KEY (source_id, target_id, relation_type)
);

CREATE TABLE IF NOT EXISTS context.ticket_revisions (
    ticket_id text NOT NULL,
    source_commit text NOT NULL,
    source_blob text NOT NULL,
    payload jsonb NOT NULL,
    projected_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (ticket_id, source_blob)
);

CREATE TABLE IF NOT EXISTS context.projection_checkpoints (
    projection text PRIMARY KEY,
    source_identity text NOT NULL,
    item_count integer NOT NULL,
    projected_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS context.jira_publications (
    publication_id text PRIMARY KEY,
    jira_key text,
    preview_digest text NOT NULL,
    adapter text NOT NULL,
    outcome text NOT NULL,
    payload jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS context.jira_publication_members (
    publication_id text NOT NULL REFERENCES context.jira_publications(publication_id) ON DELETE CASCADE,
    ticket_id text NOT NULL REFERENCES context.tickets(id),
    source_blob text NOT NULL,
    PRIMARY KEY (publication_id, ticket_id)
);

CREATE TABLE IF NOT EXISTS context.source_envelopes (
    source_type text NOT NULL,
    source_id text NOT NULL,
    schema_version integer NOT NULL,
    source_digest text NOT NULL,
    source_authority text NOT NULL,
    availability text NOT NULL,
    payload jsonb NOT NULL,
    projected_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (source_type, source_id, source_digest)
);

CREATE TABLE IF NOT EXISTS context.agent_leases (
    lease_id text PRIMARY KEY,
    operation text NOT NULL,
    owner text NOT NULL,
    expires_at timestamptz NOT NULL,
    metadata jsonb NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS tickets_context_state_idx ON context.tickets(context, state);
CREATE INDEX IF NOT EXISTS source_envelopes_payload_idx ON context.source_envelopes USING gin(payload);

CREATE OR REPLACE VIEW context.depends_on_edges AS
SELECT source_id, target_id, metadata
FROM context.ticket_relations
WHERE relation_type = 'depends_on';

DROP PROPERTY GRAPH IF EXISTS context.context_graph;

CREATE PROPERTY GRAPH context.context_graph
    VERTEX TABLES (context.tickets AS tickets KEY (id) LABEL ticket PROPERTIES (id, context, title, state, priority, points))
    EDGE TABLES (
        context.depends_on_edges KEY (source_id, target_id)
        SOURCE KEY (source_id) REFERENCES tickets (id)
        DESTINATION KEY (target_id) REFERENCES tickets (id)
        LABEL depends_on PROPERTIES (metadata)
    );

INSERT INTO context.schema_migrations(version) VALUES (1) ON CONFLICT DO NOTHING;

COMMIT;
