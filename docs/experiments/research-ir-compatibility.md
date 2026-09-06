# Knowledge IR compatibility disposition

Audit of implemented prototype formats at `db3040da274816b035b0093a1d49f710585a97c1`,
after storage, import and expiry collection landed. Tracked in
[issue #71](https://github.com/magnus919/groktocrawl-x/issues/71).
[ADR-0069](../adr/0069-define-versioned-knowledge-and-verification.md) is the accepted
bounded foundation contract; its body is unchanged. This document does not freeze
`knowledge-ir/1`, change an accepted ADR or report W2/W3 complete.

## Conclusion and next implementation

The prototype has substantial structural and storage validation, but **a retained
structural revision is not a complete research revision**. The complete in-memory
history model and persisted history are different contracts. Persisting a publication
preserves its research context, but does not apply the full history validator to a
chain of complete research revisions.

The next implementation should retain the existing complete fixture-revision shape
and validate successors against retained complete parents before rendering. Keep a
new explicit prototype storage discriminator and old readers. Do not rename the
current structure, publication or bundle to `knowledge-ir/1`, invent absent metadata
for old records, or change old verification hashes in place.

## Contract disposition

Paths below are under `agent-svc/agent/experimental/`. “Implemented” describes the
stated bounded fixture behavior, not independent semantic correctness or public
security. The next column is required work or an explicit retained limitation.

| ADR-0069 contract | Current implementation and boundary | Disposition |
|---|---|---|
| One versioned immutable revision with research/revision IDs and parent | `KnowledgeStructure` has schema/scope/research/revision IDs. `retained-structure-prototype/1` adds parent and canonical storage. `FixtureRevision` separately wraps complete research, parent, creation time and introductions. | Persist complete research revisions; retain structural readers as legacy, not silently complete v1 records. |
| Creation time, objective, questions/as-of, policy, coverage and unresolved questions | `FixtureRevision.created_at` enforces input chronology and non-null objective. `FixtureResearch.objective` alone is optional. Questions/conflicts and policy live under research/verifications; coverage is derived. The retained structural payload excludes those fields and creation time. | Store and validate the complete envelope. Distinguish canonical creation time from operational database timestamps. Specify explicit versus derived fields in the future interchange schema. |
| Immutable snapshot descriptor and resolvable content | `Snapshot` records URL, retrieval time, digest, normalization, text media, dates/provenance and lineage/origin. It embeds text. SourceStore separately retains exact bodies; RevisionStore validates scoped source closure. | Existing text path works. A future external content-reference representation needs a versioned resolver contract and migration, not a field rename or URL fetch during admission. |
| Exact text evidence locators | `Evidence` stores snapshot ID, code-point start/end, exact quote and UTF-8 digest; structure validation checks resolution and equality. | Preserve current text semantics. Binary/PDF locators remain intentionally inadmissible until separately specified. |
| Claim kinds, qualifiers and evidence assessment | `Claim` has all three kinds, qualifiers, temporal scope and five assessment states. `AssessmentLink` maps claims to explicit assessment records; verification inputs identify subjects. | Freeze how links appear in the consolidated schema. Do not call field-name differences a semantic failure where an explicit mapping already exists. Observation labels remain caller assertions, not authenticated measurement provenance. |
| Directed support/conflict/derivation with scoped rationale | `Relationship` has endpoint IDs, rationale, rule and assumptions; structural validation enforces direction, references and acyclic derivation. `Conflict` links one report claim/question to evidence. | Preserve deterministic checks. Document whether the narrower report-claim conflict representation fully expresses the chosen v1 cases; do not infer source independence or transitive entailment. |
| Verification subject, kind, verdict, input digest, time, reason and evidence | `FixtureVerification` and `VerificationInput` provide those fields with policy and fixture verifier identity/version. Digests bind the complete structural input. | Fixture-only verifier kind is intentional. Model/prompt provenance and authenticated machine/human identities need their own admitted representations before non-fixture use. |
| Stable IDs, predecessors and append-only verification across revisions | `FixtureHistory` checks introductions, predecessors, cross-kind IDs and immutable records across complete supplied revisions. Retained `RevisionStore.entity_records` compares snapshots/evidence/claims/relationships only. | **Primary gap:** apply complete history validation against retained complete parents, including assessments, verification, questions and conflicts. A publication's local validation does not establish this historical invariant. |
| Three rendered layers, IDs/digests and statement mappings | `RenderInput`, `FixtureArtifact`, `FixtureRenderAudit` and `FixturePublication` bind artifact set, renderer/auditor, statement/claim/evidence maps and three outputs. PublicationStore persists canonical publication plus exact output bytes and reference ledger. | Preserve the fixture manifest and audit checks. A future public manifest must pin the complete research revision identity, not silently equate structural and full research revisions. |
| Whole-envelope canonicalization | `canonical.py` supplies bounded JCS and schema-prefixed SHA-256 for retained envelopes. Verification/render input hashes use their own documented prototype serialization. | Preserve each legacy hash algorithm under its existing discriminator. JCS on an outer envelope does not retroactively make inner prototype hashes JCS. Any new algorithm gets an explicit version and golden compatibility cases. |
| Retain, re-render, export/import, deletion and expiry | Schema 6 stores sources, structural revisions and publication context; historical re-render pins original research bytes. Bundles include selected publication, structural ancestry and source closure. Imports preserve original identities with a separate recipient mapping. Expiry/deletion purges dependent copies. | These lifecycle paths are implemented and tested. Bundles do not contain complete predecessor declarations and complete research context for every structural ancestor. Extend only after complete revision persistence; keep old bundle readers and bounds. |
| Independent support/freshness/conflict/render judgment | Fixtures bind supplied verdicts and require publication eligibility; source dates/lineage and semantic outcomes are authored assertions. | Remains a separate evaluation gate. No stored hash, passing database test or fixture verifier record establishes truth, human review or calibrated judge performance. |

Source entry points: [knowledge.py](../../agent-svc/agent/experimental/knowledge.py),
[verification.py](../../agent-svc/agent/experimental/verification.py),
[publication.py](../../agent-svc/agent/experimental/publication.py),
[revisions.py](../../agent-svc/agent/experimental/revisions.py),
[revision_store.py](../../agent-svc/agent/experimental/revision_store.py),
[publication_store.py](../../agent-svc/agent/experimental/publication_store.py), and
[artifact_bundle.py](../../agent-svc/agent/experimental/artifact_bundle.py).

## Implementation order for issue #71

1. Define canonical admission of a complete fixture revision using existing typed
   validation, caller-selected scope/research/revision and an explicit parent.
   Keep the 1 MiB admission bound unless a separate measured change is justified.
   Reject missing objective/time/introduction context; do not fill it from ambient
   time, a publication or a structural revision's database row.
2. Add explicit persistence and migration with atomic receipt/current-parent/source
   closure. Validate the bounded complete retained chain before commit and reopen.
   Exercise changed/reused verification and assessment IDs, removed/reintroduced
   entities, stale parents, cross-scope references and cancellation/ambiguous commit.
3. Integrate publication and historical re-render with the complete pinned revision;
   extend export/import to include its required history with explicit format versions.
   Old stored bytes and receipt identities remain readable through old contracts.
4. Rehearse migration/restore and deletion/import/expiry closure on actual PostgreSQL.
   Update this disposition with evidence before considering a consolidated schema
   freeze or external client exposure.

These are dependent implementation steps, not authorization to widen provider,
production, public authentication, runtime or recovery scope. Split reviewable PRs
at complete transaction/format boundaries; do not call step 1 complete end-to-end
compatibility. A new database schema version alone does not version every payload.

## Compatibility and completion gates

- Keep all existing prototype discriminators and hash interpretations stable.
  Existing files/rows must not acquire missing semantic provenance during migration.
- Use explicit new envelope versions and reject unknown versions before publication;
  provide positive and negative golden examples and exact round-trip expectations.
- Preserve current size/depth/count limits or separately document and measure any
  changed bounds. ADR-0071's proposed 5 MiB IR ceiling is not the implemented 1 MiB
  canonical admission limit and must not be reported as supported capacity.
- Preserve immutable source bytes, source/ref closure, original scope identities,
  current deletion authority and complete predecessor requirements through the
  publication/export/import path. Public principal authorization remains W6 work.
- Keep independent semantic evaluation, human calibration and model/prompt provenance
  outside the claim that a structural/persistence test passed. Human fields remain
  unset; Hermes is an AI reviewer, not a human-label substitute.

The storage lifecycle's 92 real PostgreSQL cases and restore evidence are recorded
in [issue #1](https://github.com/magnus919/groktocrawl-x/issues/1#issuecomment-5557113293).
All five workflows for the audit base commit passed. This audit adds no executed
compatibility feature or additional database evidence.
