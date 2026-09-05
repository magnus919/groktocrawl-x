# Store Research Evidence Independently of Sessions

- Status: proposed
- Deciders: Magnus Hedemark
- Date: 2026-09-04
- Scope: experimental Knowledge IR persistence; `magnus919/groktocrawl-x` only
- Plan: D3 / W1 and W3; issue [#5](https://github.com/magnus919/groktocrawl-x/issues/5)
- Supersedes: none while proposed; intended impacts below

## Context and Problem Statement

Merged foundation PR #4 contains proposed contracts for immutable evidence,
versioned Knowledge IR and audited artifact sets. Their storage must survive the
expiry of a session and support reuse, export and verification against exact bytes.
The inherited session store coordinates Valkey keys and TTLs; research memory
stores cached results with separate semantic-index references. Neither contract
alone defines the retained research product proposed in ADR-0069.

The initial corpus is bounded normalized text, IR JSON and rendered text. It does
not require a general document warehouse or large binary media archive. A storage
choice should make publication and recovery inspectable without requiring a blob
service before it delivers value. A storage transaction does not make an interrupted
research workflow resume; D5 owns durable execution.

## Decision Drivers

- One authoritative copy of retained evidence and knowledge, independent of sessions.
- Atomic publication of an IR revision and its reference ledger; no completed
  artifact can point to unpublished or unavailable required inputs.
- Concurrent writers, duplicate requests, deletion, quota and garbage collection
  obey an explicit ownership/transaction contract.
- Re-rendering and export preserve content identity, scope and historical context.
- A bounded, self-hosted initial implementation with a clear growth/migration path.

## Considered Options

| Option | Benefit | Cost / reason not preferred initially |
|---|---|---|
| Retained Valkey data plus Qdrant | Reuses current services | Requires a new durable metadata/reference/retention protocol and backup contract; semantic index cannot substitute for source bytes |
| SQLite with evidence in the same database | Small deployment footprint and local transactional publication | A credible single-owner prototype; concurrent writers and later remote workers need more constrained access/coordination |
| PostgreSQL metadata plus local files or object storage | Separates large bytes from relational metadata; good growth path | Two authoritative write/delete boundaries require staging, reconciliation and coordinated restore immediately |
| PostgreSQL metadata and bounded evidence/output bytes | One transactional authority for publication, reference tracking and quotas | Adds a database service; evidence increases database/backup size and must be strictly bounded |

SQLite's single-writer constraint is documented by its maintainers; it remains a
credible alternative if single-owner local execution becomes an explicit target.
The preference for PostgreSQL here is a design judgment about expected concurrent
research work, not a measured performance result. [SQLite deployment guidance](https://www.sqlite.org/whentouse.html)

## Decision Outcome

**Recommend the fourth option**, subject to review and the confirmation gates below.
Use PostgreSQL as the authority for scope/research metadata, normalized evidence
bytes, IR revisions, render artifacts, reference ledgers and publication receipts.
Keep Valkey for ephemeral sessions/cache where useful and Qdrant for rebuildable
semantic indexes. Do not automatically migrate every existing store or choose
Temporal/LangGraph persistence in this ADR.

Store exact normalized evidence and canonical JSON bytes in bounded `bytea` values;
retain parsed JSON only as a query projection. PostgreSQL supports binary strings
through `bytea`. Its transaction isolation options require deliberate locking or
retry behavior; simply selecting PostgreSQL does not establish our invariants.
[Binary types](https://www.postgresql.org/docs/current/datatype-binary.html),
[transaction isolation](https://www.postgresql.org/docs/current/transaction-iso.html)

No PostgreSQL service, driver, migration or setting is introduced by this proposal.
The implementation PR must pin a supported version, add the opt-in Compose/profile
and configuration surface, and update deployment/API/CLI documentation as required.
Keep the inherited backend available during the isolated experiment.

### Logical records and identity

| Record | Identity and minimum responsibility |
|---|---|
| Scope quota | Server-derived `scope_id`, admitted/reserved/committed bytes, quota policy and deletion/restore generation |
| Research root | `(scope_id, research_id)`, lifecycle state, generation, current IR pointer, retention deadline and request/policy identity |
| Content blob | `(scope_id, digest)`, exact bytes and byte count; media/normalization metadata belongs to referencing descriptors, and digest equality does not authorize access |
| Snapshot | `(scope_id, research_id, snapshot_id)`, immutable source descriptor and scoped blob reference |
| IR revision | `(scope_id, research_id, revision_id)`, canonical bytes/digest, parent identity, schema/policy/verifier versions, creation time |
| Reference ledger | Exact snapshots/blobs referenced by each IR revision and render set; foreign keys bind scope and research identities |
| Render set | Immutable manifest pinning one IR revision and the summary/analysis/dossier blobs, audit record IDs and publication state |
| Operation receipt | `(scope_id, research_id, operation_id)`, input digest, committed output identities and root generation |
| Tombstone | Deleted root identity, deletion time/generation/reason class; no source body or copied claim text |

A single-operator deployment still has an explicit server-selected scope. This is
an access boundary, not a new tenancy product. Composite keys/foreign keys prevent
cross-scope references; authorization is checked on read, write, export and index
resolution. Content deduplication is scope-local, and the application must not
reveal whether another scope has matching bytes. Blob reuse must compare bytes/length and reject same-ID/different-content attempts
rather than overwrite. Distinct descriptors may reference identical bytes with
different normalization/media metadata, which is validated independently.

Roots and opaque IDs are server-created and never reused. Normal writes require an
existing active root and matching generation; missing/deleted roots cannot be
implicitly recreated by a late worker. Snapshot URLs are acquisition metadata;
identical URLs at different times may produce different snapshot IDs/content.

### Canonical representation

Use RFC 8785 JCS for IR/manifest payload serialization, with a schema version in the
payload. Store the exact canonical UTF-8 bytes alongside their digest. JSON database
projections must never be reserialized as the authoritative bytes. JCS defines
property/primitive serialization and Unicode handling; it is not equivalent to
Python's default `json.dumps(sort_keys=True)`. [RFC 8785](https://www.rfc-editor.org/rfc/rfc8785)

Define `ir-jcs-sha256/1` as SHA-256 of the UTF-8 prefix `knowledge-ir/1`, one zero
byte, then JCS payload bytes. The digest is outside the payload it hashes. Define
`render-jcs-sha256/1` analogously with prefix `render-manifest/1`. Verifier input
hashes bind the versioned, exact input subset and its declared serialization; the
existing worked example's `fixture-verifier-input/1` remains a different fixture
format and must not be relabeled as JCS.

Reject duplicate JSON keys, invalid Unicode and non-finite numbers before admission.
Restrict numeric schema fields to safe integers; encode exact decimal amounts or
larger integers as schema-defined strings. Do not apply additional Unicode
normalization after source offsets/digests are created. The implementation must
include RFC vectors, supplementary-character key ordering and round-trip checks.
Canonicalization proves repeatable byte identity, not source authenticity or truth.

### Publication, concurrency and ambiguous outcomes

Use short database transactions; no search, scrape, LLM or semantic-index request
runs while a database transaction/lock is held. Admit bounded capacity before
acquisition. Reserve byte quotas through the scope quota row, then lock research
roots in sorted-ID order when needed. All publication, quota, delete and GC paths
follow the same lock order. Choose row-locked Read Committed transactions for these
scoped mutations; use a consistent snapshot for multi-record reads/exports. Test
this choice against concurrent interleavings rather than relying on defaults.

1. **Acquire/stage snapshots.** Verify byte limits, digest and descriptor, then insert
   bytes and immutable snapshot rows in one transaction. Attach them to the root's
   staging reference set so GC cannot remove in-use inputs. Record acquisition
   completion separately from a published research artifact.
2. **Commit IR.** Lock/check active root, expected parent/generation, quota reservation
   and operation receipt. Validate the complete IR and derive its reference ledger
   from canonical content. Insert the immutable revision, ledger and receipt, convert
   reservations to committed accounting, and advance the current pointer in one
   transaction. Reject a stale parent; recompute/rebase outside the transaction.
3. **Publish a render set.** Stage bounded output bytes, then validate one pinned IR,
   required source availability and render-audit outcomes. Commit all three output
   references, manifest, accounting and publication receipt atomically. Only a
   published set is a final result; an isolated IR revision is not a completed answer.
4. **Resolve retries.** Same operation ID and input digest returns its receipt without
   another effect. Same ID with a different input fails. After connection loss around
   COMMIT, query the receipt before retrying; never infer failure from a missing ACK.

The implementation must cross-check canonical JSON references against the relational
ledger; foreign keys cannot validate arbitrary JSON content by themselves. The
ledger and manifest are inserted in the same transaction after validation. Reads
verify root lifecycle and publication status; an immutable payload does not bypass
a later deletion or authorization change.

Cancellation before transaction start prevents the write. Cancellation during an
already executing commit may leave a committed IR or render set; record/reconcile
its receipt and do not report that cancellation rolled back committed bytes. D5/D6
must define terminal job/event precedence. No completed job event or webhook is
sent just because a client lost its connection during storage publication.

### Retention, quotas and deletion

Propose the following initial operator-configurable limits, to be validated in W3.
These are design defaults, not existing environment variables or measured capacity.
Before a first published render set, the root and its unpublished revisions use the
staging deadline; publication establishes the research retention deadline:

| Item | Proposed initial value / behavior |
|---|---|
| Research retention | 30 days from latest explicitly published render set; ordinary reads/session refresh do not extend it |
| Unpublished staging | 24 hours from last valid writer activity; D5 must renew or release staging for longer jobs |
| Snapshot body | 10 MiB of normalized UTF-8 bytes maximum; reject/explicitly report excess, never silently truncate evidence |
| Canonical IR payload | 5 MiB maximum per revision |
| Research root quota | 100 MiB logical referenced/staged/reserved bytes across retained revisions and outputs |
| Scope quota | 1 GiB logical research bytes; operator can raise it before admitting more work |
| Operation receipts | Retain for at least the research lifetime and 7 days after completion/deletion; D5 may require longer |
| Tombstones | Minimum 30 days after deletion; late writes to absent roots still fail after tombstone removal |

Account logical bytes per root even if blobs deduplicate; scope totals sum root
charges. This keeps quotas deterministic across dedup changes. Physical database,
index and backup usage is separately measured and requires free-space headroom.
Bound all staging reservations and concurrent growth; a denied reservation cannot
be replaced with an unbounded in-memory buffer. On quota exhaustion, stop/degrade
explicitly; do not evict evidence promised within retention to admit new work.

Each root's retention covers the reference closure of all its retained revisions,
including older revisions needed to audit changes. Shared blobs live until every
retained or staging reference is gone. A transactional GC pass locks the scope,
rechecks roots, deadlines and references, and removes only unreferenced data. Reads
of a retained set use a consistent database snapshot; streaming export materializes
a bounded, verified bundle before that read transaction ends. Do not hold a DB
transaction open across an arbitrarily slow client download.

Explicit deletion overrides retention. In one transaction, mark the root deleted,
advance generation, deny new publications, and invalidate normal reads. A bounded
purge then removes every dependent IR, output, snapshot and unshared body; retain
only the minimal tombstone/receipt metadata. Delete semantic index/cache entries
best-effort, but always authorize/index-resolve against the authoritative root so
stale hits cannot reveal deleted evidence. A targeted source purge must also
invalidate/purge every dependent artifact and quoted span, not only the raw blob.
D6 must document the externally visible unavailable/deleted result.

### Export, backup, restore and migration

A portable export contains a versioned manifest, one selected IR revision plus its
necessary predecessor/verification dependencies, all required snapshot bodies,
selected render set, byte digests and schema/normalization identifiers. Resolve
local bundle paths rather than fetching external URLs. Export strips operational
secrets and does not carry usable access tokens. Enforce access and size limits.

Import verifies all bytes, schema versions, scopes, references, retention and
canonicalization before transactional publication. Stage first, reject malformed,
unsupported or conflicting identities, and apply the recipient's authorization
scope through an explicit envelope mapping. Do not rewrite embedded canonical IR
bytes to change scope. Imported artifacts are historical evidence; import never
resumes a job, sends a webhook or treats old facts as current. No automatic import
of cached prose as verified claims.

Database backups must include bytes, metadata, receipts and deletion records from
a consistent point. A SQL dump is a supported PostgreSQL backup mechanism; a
successful dump alone is not a restore test. [PostgreSQL backup documentation](https://www.postgresql.org/docs/current/backup-dump.html)

Before an opt-in pilot, rehearse a restore of the bounded corpus into an isolated
database and verify every manifest, byte digest and reference ledger. Record actual
backup age, data loss window, elapsed recovery time and image/schema versions;
set the pilot RPO/RTO from those measurements in D5. This ADR makes no availability
SLO or claim that database contents survive loss of an unbacked volume.

Restores remain quarantined until current retention and post-backup deletions have
been reconciled. A pre-deletion backup must not automatically re-expose deleted
research. Preserve/export a deletion inventory separately from the backup being
restored, or keep access blocked when the required history is unavailable. Operators
must explicitly reconcile that uncertainty; an old backup cannot reconstruct
unknown later deletions. Rebuild Qdrant/cache projections from authorized retained
roots. Do not restore pending work as runnable merely because receipts exist.

Introduce storage in an isolated experimental database/namespace. Use forward
schema migrations with a pre-migration backup, compatibility checks and a restore
rehearsal. Keep readers for retained schema versions or provide a reviewed migration
that creates new revisions without mutating signed/hashed history. Moving large
bytes to object storage is a future ADR triggered by measured capacity/backup cost;
its dual-store publication and restore protocol must be demonstrated before cutover.

## Inherited Decision Impact

| Record | Intended relationship on adoption | Scope |
|---|---|---|
| ADR-0019 | Retain scrape-cache role | A scrape cache is not authoritative retained evidence |
| ADR-0026–0028 | Retain retrieval intent; extend migration/retention | Qdrant remains a derived index; loss/rebuild does not erase evidence |
| ADR-0040/0041 (proposed) | Replace storage authority for the experimental path | Session TTL and cached prose no longer own retained research |
| ADR-0049 | Retain compatibility intent; supersede TTL freshness basis for IR | Source freshness and research retention are separately recorded; old cached-answer rules remain for the inherited path |
| ADR-0050/0059 | Extend | Request/pass artifact reuse feeds immutable retained snapshots |
| ADR-0063/0066 | Leave inherited session operations in place pending D6 | New research publication does not reuse the session lock/TTL protocol as its authority |
| ADR-0047 | Storage boundary only; D5 owns supersession | PostgreSQL transactions do not settle job leases, retries, scheduling or webhook durability |

No inherited status changes while this record is proposed. Any acceptance must
record exact experimental scope and update relevant implementation/operator docs.

## Consequences

The initial research product has one authoritative transactional boundary and a
clear retention/restore contract. It adds a database and grows backup volume;
strict bounds may reject large documents and require user-visible partial results.
Database availability becomes necessary for publication. Per-scope quota locking
may become a bottleneck; measure before replacing it with more complex accounting.
The design deliberately leaves workflow-runtime and job recovery choices open.

## Confirmation

The storage owner must run the [lifecycle and failure matrix](../experiments/research-storage-lifecycle.md)
against a real isolated PostgreSQL instance before W3 passes. Check concurrent
publication/deletion/GC/quota races, ambiguous commits, scopes, JCS vectors, expiry,
export/import and restore. Verify no orphaned published references, no silent
truncation, no resurrected deleted root and no provider work during storage retries.
Record version, corpus bounds, tested interleavings, latency/storage/backup metrics
and untested failure modes under ADR-0070 evidence rules.

Magnus reviews the database choice and limits before implementation. W3 must show
acceptable footprint and bounded publication/backup behavior with the declared
100 MiB/root and concurrent workload. If not, revisit SQLite or external blobs
through evidence rather than silently weakening limits or invariants.

## Links

- [Execution boundaries](0068-separate-research-execution-knowledge-and-rendering.md)
- [Knowledge IR](0069-define-versioned-knowledge-and-verification.md)
- [Evaluation gates](0070-evaluate-research-policy-and-runtime-separately.md)
- [Lifecycle example](../experiments/research-storage-lifecycle.md)
- [Experiment plan](../experiments/research-architecture.md)
