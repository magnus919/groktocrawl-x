BEGIN;

CREATE TABLE research_staging.slopsearx_provenance_references (
    scope_id uuid NOT NULL,
    research_id uuid NOT NULL,
    result_id text NOT NULL,
    reference jsonb NOT NULL,
    reference_digest text NOT NULL,
    remote_expires_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (scope_id, research_id, result_id),
    FOREIGN KEY (scope_id, research_id)
        REFERENCES research_staging.research_artifact_sets(scope_id, research_id)
        ON DELETE CASCADE,
    CHECK (length(result_id) BETWEEN 1 AND 300),
    CHECK (reference_digest ~ '^[0-9a-f]{64}$'),
    CHECK (octet_length(reference::text) <= 8192)
);

CREATE INDEX slopsearx_provenance_expiry_idx
    ON research_staging.slopsearx_provenance_references(remote_expires_at);

UPDATE research_staging.schema_version SET version = 15;

COMMIT;
