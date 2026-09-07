# Durable backup and restore evidence

This packet defines the W5 backup/restore rehearsal for the experimental durable
research route. It is evidence for issue [#147](https://github.com/magnus919/groktocrawl-x/issues/147)
and proposed [ADR-0078](../adr/0078-define-durable-research-backup-and-artifact-authority.md).
It is not a production disaster-recovery claim.

## Hosted evidence

- Runtime CI run: [34142290308](https://github.com/magnus919/groktocrawl-x/actions/runs/34142290308)
- Tested commit: `7b1523dcd3062da2600eb2f395384e94b3577310`
- Integration job: [101808522545](https://github.com/magnus919/groktocrawl-x/actions/runs/34142290308/job/101808522545)
- PostgreSQL Storage Probes job: [101808522538](https://github.com/magnus919/groktocrawl-x/actions/runs/34142290308/job/101808522538)
- Twin Contracts job: [101808522507](https://github.com/magnus919/groktocrawl-x/actions/runs/34142290308/job/101808522507)
- Runtime Gate: passed
- Run conclusion: `success` on 2026-09-07

The hosted run passed the W5 recovery matrix, integration tests, PostgreSQL storage
probes, twin contracts and the fail-closed Runtime Gate. The focused local suite
reported 10 passed before the PR was opened.

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
| Completed run with terminal artifacts | Result, event history and artifact bytes reopen with identical digests | Local and hosted W5 validation passed |
| Idempotency retry after restore | Same request key returns the original run identity | Local and hosted W5 validation passed |
| Running run at backup time | No old lease is restored; a new owner can reclaim it | Local and hosted W5 validation passed |
| Deletion before backup | Tombstone survives restore and text-bearing reads fail closed | Local and hosted W5 validation passed |
| Altered snapshot digest or value | Restore rejects before changing the target | Local and hosted W5 validation passed |
| Non-empty target without explicit replacement | Restore rejects rather than overwriting state | Local and hosted W5 validation passed |

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
