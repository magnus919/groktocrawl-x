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
