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
