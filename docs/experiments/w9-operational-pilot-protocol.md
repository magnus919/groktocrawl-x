# W9 bounded operational pilot protocol

Status: **frozen before the pilot began**

## Question and decision

Can the isolated candidate remain healthy and complete representative inherited
and experimental research work over a real observation window without losing
artifact authority, vector consistency, client compatibility, or rollback
readiness?

Passing permits the final W9 adoption decision. It does not make the candidate a
mainline replacement or prove production scale.

## Window and minimum exposure

- Start: `2026-09-11T17:26:19Z`
- Earliest completion: `2026-09-18T17:26:19Z`
- Required exposure: at least seven elapsed days **and** at least 30 successful
  representative requests. Both conditions are mandatory.
- Checkpoints: start, no earlier than 72 elapsed hours, and no earlier than 168
  elapsed hours. A delayed checkpoint extends the pilot; it never shortens it.

Each checkpoint runs the frozen candidate compatibility suite: scrape, bounded
crawl, search, synchronous and streaming answer, synchronous and streaming
agent, webhook, CLI scrape/search, and MCP scrape/search. It also runs the
cross-client experimental research verification. This yields at least 12
declared user operations per checkpoint and at least 36 over three checkpoints.
Health probes and job-status polling do not count toward the request minimum.

## Frozen boundaries

- Candidate: `groktocrawl-x-candidate` on `gpuslut01`, loopback API and MCP ports.
- Search: the pinned SlopSearX image already matched to the incumbent.
- Inference: LiteLLM's `local` model through the incumbent home-lab TLS route.
- Artifact authority: PostgreSQL schema 14.
- Semantic serving: pgvector, with Qdrant retained as the tested rollback copy.
- Fixtures and operation bounds: the W9 compatibility protocol.

No cache is deliberately cleared between checkpoints. No failed attempt is
discarded. Configuration or code changes restart the seven-day window unless
they only correct observation tooling and leave the deployed candidate revision
and runtime configuration unchanged.

## Observations

At every checkpoint retain:

- the sanitized compatibility and cross-client verification receipts;
- the exact deployed revision and provider/model identities;
- terminal outcomes, failure classes, and per-operation latency distributions;
- artifact-set, vector-provider, and client-path reconciliation results;
- point-in-time service health and bounded resource observations.

The 10-minute roadmap heartbeat checks CI and candidate health. It stays quiet
while healthy and records or reports only a material state change, failure,
completed gate, or required user action.

## Pass and stop rules

Pass only after both time and request thresholds when:

1. every declared request has a terminal receipt, with no unexplained
   candidate-only contract failure;
2. experimental research artifacts remain identical across HTTP, SSE, CLI, and
   MCP retrieval paths;
3. PostgreSQL remains authoritative, pgvector remains the serving provider, and
   Qdrant remains healthy and count-consistent as the rollback copy;
4. no retained deletion reappears and no backup/restore or reconciliation alarm
   remains unresolved;
5. observed latency or resource behavior shows no repeated material regression
   that would prevent ordinary home-lab operation.

Stop and preserve evidence on unexplained data loss, authority ambiguity,
repeated failed completion, rollback-copy divergence, or a required candidate
runtime change. A single transient dependency failure is recorded and retried
once; it is not silently converted into a pass.

## Limits

This pilot uses one home-lab candidate, a small fixed fixture set, and three
scheduled suites. It does not measure multi-user saturation, regional failure,
Internet-wide acquisition, physical disaster recovery, or production support
load. Resource snapshots on this host are diagnostic rather than capacity proof.
