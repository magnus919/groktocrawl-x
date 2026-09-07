# Durable backup and restore evidence

This packet defines the W5 backup/restore rehearsal for the experimental durable
research route. It is evidence for issue [#147](https://github.com/magnus919/groktocrawl-x/issues/147)
and proposed [ADR-0078](../adr/0078-define-durable-research-backup-and-artifact-authority.md).
It is not a production disaster-recovery claim.

## Authority boundary

The Valkey durable ledger is authoritative for admitted run identity, idempotency
receipts, ownership generation, checkpoints, terminal state, retention and deletion
tombstones. The fixture route's bounded terminal payload is authoritative for the
published manifest, artifact bytes and terminal event history. The execution
process-local map is only a projection and may be discarded.

The current terminal payload remains bounded by the route's 1 MiB encoded limit and
each manifest/artifact body is checked against its SHA-256 digest. A production-sized
artifact store is still an open W5 decision; no external object store is implied by
this packet.

## Snapshot contract

`DurableResearchLedger.export_snapshot()` copies retained keys in one namespace,
including run records, idempotency receipts and the run index. Ephemeral lease keys
are deliberately excluded. Every entry records its remaining TTL, encoded dump and
value digest; the snapshot has a schema version and canonical whole-snapshot digest.

`restore_snapshot()` validates the entire snapshot before mutation and restores in a
single Redis transaction into an empty target or an explicitly replaced namespace.
Restored `running` records have no lease and are therefore reclaimable. Terminal
receipts and deletion tombstones remain retained with their original TTL bounds.

## Required rehearsal cases

| Case | Expected result | Status |
|---|---|---|
| Completed run with terminal artifacts | Result, event history and artifact bytes reopen with identical digests | Focused local test passed; hosted evidence pending |
| Idempotency retry after restore | Same request key returns the original run identity | Focused local test passed; hosted evidence pending |
| Running run at backup time | No old lease is restored; a new owner can reclaim it | Focused local test passed; hosted evidence pending |
| Deletion before backup | Tombstone survives restore and text-bearing reads fail closed | Focused route test passed; hosted evidence pending |
| Altered snapshot digest or value | Restore rejects before changing the target | Focused local test passed; hosted evidence pending |
| Non-empty target without explicit replacement | Restore rejects rather than overwriting state | Focused local test passed; hosted evidence pending |

The hosted packet must record the commit, Valkey version/configuration, namespace,
retention settings, target state, counts, elapsed restore time and any excluded
failure schedules. Passing these cases does not establish disk-loss, regional,
encrypted-backup or cross-version recovery.

## Remaining W5 decision

The experiment still needs an explicit production artifact-authority decision. The
current bounded inline payload is sufficient for fixture evidence and recovery
contract tests. Before production adoption, compare an external artifact store or
PostgreSQL-backed artifact authority against the stated size, retention, integrity,
backup, migration and operational requirements. Do not close W5 or accept ADR-0074
from this rehearsal alone.
