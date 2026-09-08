# PostgreSQL + pgvector versus Qdrant evaluation

Status: **evaluation plan only; no production storage change and no Qdrant removal decision**.

The experimental architecture is considering one PostgreSQL authority for evidence and metadata. If that direction is accepted, the vector index should be tested as part of the same decision. The current stack uses Qdrant behind `semantic-svc` for embeddings and similarity search, while Valkey-backed records remain the artifact authority for the inherited research-memory path. This document defines a reversible comparison; it does not assume that PostgreSQL should replace Qdrant.

## Candidates and constants

| Candidate | Vector/index role | Evidence authority during the test |
|---|---|---|
| Qdrant reference | Existing Qdrant collection and distance/index settings | Existing fixture artifact records |
| PostgreSQL + pgvector | PostgreSQL extension with an equivalent vector column, distance operator and metadata filters | The same fixture artifact records |

Both candidates must receive identical embedding bytes, model identity, dimensions, normalization, source IDs, lineage IDs, tenant/scope fields, deletion state, expiry timestamps and top-k requests. Embedding generation and reranking stay outside this storage comparison. The comparison uses a pinned synthetic corpus first; it must not read or mutate production collections.

## Workloads

Run each workload in cold and warm conditions with the same host limits and reset procedure:

1. bulk insert with metadata and duplicate/idempotent replays;
2. top-k similarity search at several result limits and score thresholds;
3. mixed concurrent search and insert traffic;
4. scope-filtered search with foreign-scope negative controls;
5. expiry and deletion propagation, including an orphaned-index reference;
6. restart, index rebuild and backup/restore rehearsal;
7. model/dimension migration with old and new vectors present; and
8. failure injection during write, commit acknowledgement and cleanup.

The workload manifest must pin corpus and embedding hashes, vector dimension, distance metric, filter fields, row/point counts, concurrency, request mix, timeouts, cache state, randomization seed and stop conditions. Every workload keeps its full failure record; timeouts and malformed responses are failed trials.

## First harness

The opt-in Compose file [`compose.vector-evaluation.yml`](../../../compose.vector-evaluation.yml)
starts a private PostgreSQL+pgvector service and a separate Qdrant service on
loopback-only ports. It is intentionally a different Compose project from the
application stack. With Docker Compose v2 and a private password:

```sh
export VECTOR_EVAL_POSTGRES_PASSWORD='use-a-private-value'
docker compose -f compose.vector-evaluation.yml --profile vector-eval up -d --wait
python scripts/run_vector_store_evaluation.py \
  --qdrant-url http://127.0.0.1:16333 \
  --postgres-dsn 'postgresql://vector_eval:use-a-private-value@127.0.0.1:15432/vector_eval' \
  --allow-isolated-database \
  --cleanup \
  --output /tmp/groktocrawl-x-vector-evaluation.json
docker compose -f compose.vector-evaluation.yml --profile vector-eval down
```

The harness uses a synthetic 3-dimensional corpus, a unique collection/table
per run, filtered searches for two scopes, duplicate replay and a soft-delete
check. It records provider failures instead of retrying them. The output is an
evaluation artifact only: it does not select a backend, alter the inherited
Qdrant collection, or claim production performance. By default it runs one
round. `--rounds N` repeats the workload against the same initialized provider
resources, preserving each round in the artifact and aggregating latency and
gate results. The first round follows provider initialization; later rounds
are warm passes and must not be presented as cold-start measurements.

The fork also provides a manual [`Vector Store Evaluation`](../../../.github/workflows/vector-store-evaluation.yml)
workflow. Run it from the repository Actions page when a hosted Docker runner
is available; it runs the harness inside the private Compose network (so the
comparison does not depend on runner host-port behavior), uploads the JSON
packet, and fails closed if either candidate has provider errors or violates a
fixture gate. The workflow defaults to three repeated warm rounds; override the
`rounds` input when a different bounded sample is needed. Set
`fresh_each_round=true` for repeated provider initialization; that mode
recreates the isolated collection and table before every round and still does
not model restart or recovery. The optional `concurrency_workers` and
`concurrency_operations` inputs run a bounded mixed search/idempotent-upsert
workload with one provider client per worker; they are incompatible with fresh
rounds and remain disabled by default. Review that packet before proposing an
ADR change.

The separate manual [`Vector Store Restart Evaluation`](../../../.github/workflows/vector-store-restart-evaluation.yml)
workflow seeds both isolated providers, restarts their containers, reconnects
without recreating the collection or table, and verifies retrieval plus
deletion continuity. It is restart evidence only; it does not replace the
backup/restore rehearsal or establish recovery authority.

The manual [`Vector Store Backup Evaluation`](../../../.github/workflows/vector-store-backup-evaluation.yml)
workflow creates a Qdrant collection snapshot and a PostgreSQL custom-format
`pg_dump`, restores each into fresh isolated services, applies the checked-in
deletion authority manifest, and verifies retrieval and deletion continuity.
It records backup bytes and hashes, restore timing, the manifest hash, and
provider failures as evidence. A successful rehearsal proves only that this
fixture can be recovered with the tested procedure; it does not authorize
production migration or removal of Qdrant.

The successful hosted rehearsal is preserved in the [fresh-target backup/restore
evidence packet](../evidence/storage-vector-evaluation/2026-09-08-backup-restore/).

## Measures and gates

Record p50/p95/p99 latency, throughput, error and timeout rate, index-build/rebuild time, CPU/RAM/disk footprint, backup size, restore time, and cleanup lag. For retrieval, report exact top-k identity overlap, score ordering changes, recall against a separately computed brute-force reference on the fixture corpus, and scope/deletion correctness. Do not treat Qdrant as truth merely because it is the incumbent.

A candidate can replace the current index only if all of these are satisfied:

- no tested cross-scope result, stale/deleted result, duplicate committed effect or dangling evidence reference;
- retrieval parity and any quality difference are reported with fixed denominators and uncertainty, not a single average;
- cold and warm performance bounds are frozen before the comparison and include rebuild, backup and restore costs;
- model/dimension migration and rollback are demonstrated; and
- removing Qdrant actually reduces operational surface without weakening recovery, retention, deletion or incident response.

If any gate is missing or inconclusive, retain Qdrant and document the measured reason. A PostgreSQL decision must be a new reviewed ADR or an explicit update to the proposed storage ADR; it must not be inferred from structural tests or a successful local boot.

## Execution boundary

This plan is intentionally separate from the W1 quality comparison. It can be prepared with deterministic fixtures before the held-out packet is frozen, but no provider-backed quality conclusion, production migration, volume deletion or Qdrant shutdown is authorized by this document. The first implementation step is a local fixture harness that can run both candidates against the same manifest and emit sanitized evidence.
