# W9 replacement readiness decision

Status: **draft; the operational pilot is still running**

## What this decision means

This report decides whether the architecture built in `magnus919/groktocrawl-x`
is credible as the next stack for this experimental repository. It does not
replace mainline GroktoCrawl, migrate the incumbent deployment, or propose an
upstream merge. Those would require separate decisions.

No final recommendation is made before the seven-day operational window ends.
The tables make the remaining judgment visible without treating pending evidence
as a pass.

## Readiness in ordinary language

The candidate can already do the incumbent's declared HTTP, streaming, CLI, and
MCP work. Its retained research data survives backup and restore, PostgreSQL is
the authoritative record, pgvector serves semantic search, and the retained
Qdrant copy can take over and return control within the rehearsal limit.

What remains is time under operation. The candidate must stay healthy through
the middle and final pilot checkpoints. The adaptive-query study is separate: it
decides whether bounded follow-up searching improves research, not whether the
candidate deployment can run safely.

## Roadmap verification matrix

| Roadmap requirement | Current judgment | Direct evidence | Remaining gate |
|---|---|---|---|
| Experimental identity and separation from mainline | Satisfied | [Architecture plan](research-architecture.md), ADR-0067, separate repository and deployment names | Preserve this wording in the final recommendation |
| New ADRs may overturn inherited decisions with scoped history | Partly satisfied | ADR-0068 through ADR-0079 and their predecessor maps | Disposition proposed ADR-0073 and ADR-0076 through ADR-0078 |
| Explicit workflow state and bounded reasoning | Satisfied for the experimental surface | [Execution confirmation](research-execution-confirmation.md), [runtime comparison](runtime-comparison/report.md), ADR-0073 evidence | Keep the typed imperative runtime as the reference; state the optional LangGraph scope |
| Durable reusable knowledge and artifact layers | Satisfied for the bounded candidate | [Complete history storage](research-complete-history-storage.md), [artifact bundles](research-artifact-bundles.md), [consolidated journey](research-consolidated-journey.md) | Retain stated scale and tenancy limits |
| Recovery and honest client streaming | Satisfied in failure injection and rehearsal | [Recovery ownership](recovery-ownership-contract.md), [backup and restore](durable-backup-restore.md), [client conformance](client-protocol-conformance.md), [migration rehearsal](evidence/replacement-rehearsal/2026-09-11-migration-rollback/) | Complete the live pilot without an unresolved authority or replay failure |
| Framework and research-quality evidence | Partly satisfied | [W7 outcome](enterprise-evaluation/w7-candidate-d-outcome-2026-09-11.md), [W8 source equivalence](enterprise-evaluation/w8-source-equivalence-outcome-2026-09-11.md), runtime/future-capability packets | Finish W10 before changing the fixed-query default |
| Repository and release standards | Satisfied to date | Required CI, architecture checks, isolated image/service names, focused reviewed PRs | Final PR must pass the same gates and leave roadmap, ADR index, README, and issues consistent |

## Replacement dimensions

| Dimension | Current result | Practical meaning |
|---|---|---|
| Research quality | Pending W10; W7 rejected Candidate D and W8 retained fixed-query retrieval | The substrate is useful, but no rejected policy is smuggled into the candidate |
| Incumbent compatibility | Passed, three repetitions per deployment | No candidate-only regression appeared in the declared journeys |
| Data durability and authority | Passed in bounded backup, fresh restore, and reconciliation tests | PostgreSQL can remain the authoritative retained store under tested conditions |
| Client parity | Passed for HTTP, SSE, polling, CLI, and MCP inventory | The same research artifact can be reached through the supported client paths |
| Migration and rollback | Passed after two preserved tooling failures and one clean idempotent run | The operator can return to Qdrant and back to pgvector without deleting either store |
| Resource and scale behavior | Bounded evidence only | Suitable for this home-lab candidate; multi-user saturation and regional resilience remain unproven |
| Operator burden | Ten candidate services plus one retained rollback store during the pilot | Removing Qdrant may simplify steady state later, but only after the rollback window and in a separate reversible change |
| Operational stability | Pending | Checkpoint 0 passed 12 requests; checkpoint 1 and the final checkpoint are time-gated |

## ADR disposition prepared for the final checkpoint

| ADR | Evidence-supported disposition if the pilot passes | What would change it |
|---|---|---|
| ADR-0073, runtime comparison | Accept the typed imperative controller as reference and LangGraph as an optional advanced runtime | A W10 or pilot failure attributable to the runtime boundary |
| ADR-0076, retained model-reviewed publications | Accept for the bounded experimental route | Publication admission or revalidation failure |
| ADR-0077, trusted bundle import | Accept for the bounded experimental route | Origin-authority, replay, or tamper rejection failure |
| ADR-0078, durable backup and authority | Accept for the bounded experimental route | Backup/restore mismatch, ambiguous authority, or unreconciled partial state |
| ADR-0079, PostgreSQL and pgvector | Already accepted for the experimental deployment | Pilot divergence or inability to execute the retained Qdrant rollback |

These are prepared dispositions, not status changes. The final PR updates each
ADR only after its remaining evidence gate passes.

## Decision gate

The candidate may be recommended for continued use in the experimental fork
only when:

1. the pilot reaches seven elapsed days and at least 30 successful representative
   requests;
2. all three checkpoints pass without unresolved data, authority, compatibility,
   or rollback failure;
3. the final evidence package preserves every failure and limitation;
4. proposed ADRs receive evidence-based statuses; and
5. the recommendation still states that experimental-fork adoption does not
   replace mainline or authorize incumbent migration.

Until then, the decision is **pending**, not failed and not provisionally passed.
