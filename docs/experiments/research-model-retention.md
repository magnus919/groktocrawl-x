# Model-reviewed consolidated retention

This W3 slice extends the isolated consolidated PostgreSQL store so its existing
transaction can retain a candidate with `fixture_only=false`. The field is a
provenance marker: it does not mean human review, semantic truth, freshness or
production approval. The same exact-byte checks, source bindings, execution-owner
receipts, report audits, root fencing, quota, expiry and deletion rules still apply.

Migration `011_consolidated_model_publications.sql` advances the isolated schema from
10 to 11 and removes only the database constraint that forced every row to be a
fixture. Schema 10 remains readable during the migration window. The migration is
opt-in and does not alter the incumbent deployment, public API, LiteLLM gateway,
Qdrant, or runtime/recovery ownership.

The real-query runner remains ephemeral until it produces a fully eligible candidate.
The latest `local` probe produced historically scoped claims but failed closed during
model review; no model publication was retained. A future successful candidate must
run the migration, stage exact source snapshots, and commit through the same fenced
transaction. Failed or indeterminate checks cannot be converted into a retained
success.

The retained consolidated publication can now be exported as the versioned
`retained-consolidated-bundle-prototype/1` format. The bounded bundle contains
the canonical checked knowledge and render manifest, exact source descriptors
and bodies, all three audited output layers, the explicit provenance marker,
receipt digest and retention deadline. Offline admission rechecks canonical
bytes, source/body hashes, output mappings, knowledge history, render audits and
publication eligibility without fetching a URL or invoking a model. This is an
export and revalidation boundary only; cross-scope import, recipient authority,
recovery ownership and production adoption remain open gates.

The next W3 slice extends the shared trusted-server import lifecycle under proposed
[ADR-0077](../adr/0077-trusted-consolidated-bundle-import.md). A schema-12 recipient
reservation records the origin scope/root/operation, origin generation, bundle and
context digests, quota charge, bounded grant and clamped retention. Commit and read
require the origin to remain a live consolidated root with the same current operation;
the bundle is admitted again before any write or read, and its digest is the idempotent
receipt. Existing origin deletion and expiry collection therefore purge or deny the
recipient copy. This remains an experimental trusted-server path; backup/restore,
public authentication and production data movement are separate decisions.
