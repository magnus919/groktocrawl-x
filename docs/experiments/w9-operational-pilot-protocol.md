# W9 bounded operational pilot protocol

Status: **real client traffic pilot active; checkpoint 0 passed**

## Question and decision

Can the isolated candidate remain healthy and complete representative inherited
and experimental research work over a real observation window without losing
artifact authority, vector consistency, client compatibility, or rollback
readiness?

Passing permits the final W9 adoption decision. It does not make the candidate a
mainline replacement or prove production scale.

## Window and minimum exposure

- Restarted: `2026-09-19T13:42:50Z`
- Earliest completion: `2026-09-26T13:42:50Z`
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

- Candidate: `groktocrawl-x-candidate` on the candidate host, with key-protected API port 18080 and allowlisted MCP port 18002 published on the trusted home-lab and
  Tailscale interfaces.
- Search: the pinned SlopSearX image already matched to the incumbent.
- Inference: LiteLLM's `local` model through the incumbent home-lab TLS route.
- Artifact authority: PostgreSQL schema 14.
- Semantic serving: pgvector, with Qdrant retained as the tested rollback copy.
- Fixtures and operation bounds: the W9 compatibility protocol.

No cache is deliberately cleared between checkpoints. No failed attempt is
discarded. Configuration or code changes restart the seven-day window unless
they only correct observation tooling and leave the deployed candidate revision
and runtime configuration unchanged.

The original window failed after a host restart: the private environment and
PostgreSQL secret bind sources had been placed under volatile temporary storage,
so Compose could not recreate the stopped containers. The outage remains in the
evidence record. Moving the same private values to persistent per-user storage
changed the operational configuration boundary, so the pilot restarted. The
candidate source and runtime image revisions did not change.

The corrected loopback-only window then passed checkpoint 0. It was deliberately
ended on 2026-09-19 when the owner chose to route normal client use through the
candidate. Publishing the API and MCP ports on the trusted home-lab and Tailscale
interfaces changed the operational configuration boundary, so the clock and
successful-operation count restarted again. The earlier checkpoint remains valid
evidence about the loopback configuration, but it does not count toward this
real-use window. The new window passed checkpoint 0 at `2026-09-19T13:51:26Z` with all 12 declared operations
successful.

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
