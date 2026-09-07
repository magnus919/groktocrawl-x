# W3 restore rehearsal evidence

This is a partial W3 evidence packet for the experimental fork. It records the
latest full PostgreSQL Runtime CI probe and keeps the remaining acceptance gaps
explicit. It is not a production recovery, disaster-recovery, or restart-SLO
claim.

## Source and run identity

- Runtime CI run: [34098769868](https://github.com/magnus919/groktocrawl-x/actions/runs/34098769868)
- Tested commit: `ea7556a8dcae55185977fbcd392fd9f82d6219a0`
- PostgreSQL job: [101668216656](https://github.com/magnus919/groktocrawl-x/actions/runs/34098769868/job/101668216656)
- Run conclusion: `success` on 2026-09-07
- Workflow path: `.github/workflows/runtime.yml`, PostgreSQL Storage Probes

The job exercised schema-one through schema-nine restore probes before the
dedicated source and consolidated restore rehearsals. The database was isolated
with a run-specific Compose project and a clean restore database.

## Observed results

| Evidence | Result | Artifact |
|---|---|---|
| Source-store PostgreSQL version | `17.11 (Debian 17.11-1.pgdg12+2)` | [source-storage-restore-result](https://github.com/magnus919/groktocrawl-x/actions/runs/34098769868/artifacts/10009872359) |
| Live source bytes verified after restore | `240` | [source-storage-restore-result](https://github.com/magnus919/groktocrawl-x/actions/runs/34098769868/artifacts/10009872359) |
| Current deletion inventory entries | `435` | [source-storage-restore-result](https://github.com/magnus919/groktocrawl-x/actions/runs/34098769868/artifacts/10009872359) |
| Post-backup deletion denied after restore | `true` | [source-storage-restore-result](https://github.com/magnus919/groktocrawl-x/actions/runs/34098769868/artifacts/10009872359) |
| Live receipt references resolve | `true` | [source-storage-restore-result](https://github.com/magnus919/groktocrawl-x/actions/runs/34098769868/artifacts/10009872359) |
| Consolidated retained bytes exact | `true` | [consolidated-storage-restore-result](https://github.com/magnus919/groktocrawl-x/actions/runs/34098769868/artifacts/10009877999) |
| Consolidated deleted resources unavailable | `true` | [consolidated-storage-restore-result](https://github.com/magnus919/groktocrawl-x/actions/runs/34098769868/artifacts/10009877999) |
| Consolidated deleted rows purged | `true` | [consolidated-storage-restore-result](https://github.com/magnus919/groktocrawl-x/actions/runs/34098769868/artifacts/10009877999) |
| Consolidated deletion receipt preserved | `true` | [consolidated-storage-restore-result](https://github.com/magnus919/groktocrawl-x/actions/runs/34098769868/artifacts/10009877999) |

The workflow also rejected a restore with no deletion inventory and a restore
with an incomplete inventory before applying the complete inventory. The
consolidated rehearsal likewise rejected missing and stale deletion inventories.
Those negative controls are visible in the PostgreSQL job log around the
dedicated restore steps.

## Acceptance status

This evidence supports bounded PostgreSQL restore, exact retained bytes, scope /
receipt checks, and post-backup deletion denial for the checked fixtures. It does
not close issue #122 because:

- `post_backup_expiry_collection_reconciled` was `false` in the source-store
  result and needs an explicit expiry/collection decision.
- The workflow has no injected interrupted restore or corrupted backup-member
  case; those failures remain untested acceptance criteria.
- The source result reports zero complete-research revisions/publications because
  those checks are represented by the separate consolidated result; the evidence
  packet does not infer counts that the artifacts do not report.
- One successful fixture restore does not establish operator recovery, physical
  loss tolerance, capacity, latency, or production deletion authority.

Keep issue [#122](https://github.com/magnus919/groktocrawl-x/issues/122) open until
the missing failure matrix and expiry reconciliation are captured in a later
run. The W3 plan must continue to distinguish this evidence from W5 durable
execution and W7 adoption claims.
