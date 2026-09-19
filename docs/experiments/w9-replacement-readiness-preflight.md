# W9 replacement-readiness preflight

- Status: **preflight complete; operational pilot and architecture decision pending**
- Candidate repository: [`magnus919/groktocrawl-x`](https://github.com/magnus919/groktocrawl-x)
- Architecture decider: Magnus Hedemark (`magnus919`)
- Decision issue: [#312](https://github.com/magnus919/groktocrawl-x/issues/312)
- Frozen candidate revision: `e4301eb32dd3b1e4ef83aec658fba754a2be31ec`
- Earliest decision date: `2026-09-26T02:19:40Z`

**This experimental fork does not replace mainline GroktoCrawl by itself.** A
successful W9 decision can adopt the candidate for continued use in this fork.
Any mainline proposal, production migration, or upstream release requires a
separate decision and its own evidence.

## What can be decided now

The candidate has passed its freeze and isolated deployment, incumbent-compatible
journeys, migration and rollback rehearsal, durable recovery checks, client-path
parity, and the PostgreSQL/pgvector serving cutover. These results support a
conditional recommendation to **adopt the candidate for the experimental fork**
if the restarted operational pilot passes its remaining checkpoints.

The recommendation is not final. The first operational window failed after a
host restart because private bind sources were stored under volatile `/tmp` paths.
That failure is retained. The corrected window started on 2026-09-19 with
persistent private configuration, and checkpoint 0 passed. Checkpoint 1 cannot
count before 2026-09-22; the final checkpoint and decision cannot count before
2026-09-26.

## Requirement-by-requirement matrix

| Requirement | Current finding | Evidence | Final action |
|---|---|---|---|
| Candidate is frozen, reproducible, and isolated from mainline | Passed | [Candidate freeze receipt](evidence/replacement-rehearsal/2026-09-11-candidate-freeze/README.md) | Confirm the final pilot used the frozen candidate revision. |
| Inherited user journeys behave like the incumbent | Passed in three matched runs per arm | [Compatibility packet](evidence/replacement-rehearsal/2026-09-11-compatibility/README.md) | Link the final checkpoint receipts; investigate any candidate-only difference. |
| Research quality is strong enough to justify the architecture | Passed only for the bounded architecture assembled from accepted slices; two attempted answer-policy replacements were rejected | [W1 comparison](enterprise-evaluation/w1-comparison-outcome-2026-09-10.md), [W7 comparison](enterprise-evaluation/w7-candidate-d-outcome-2026-09-11.md), [W10 evidence index](evidence/adaptive-policy/w10-final/00-index.md) | State clearly that adoption retains the fixed retrieval and generalist defaults selected by the experiments. |
| Durable execution survives interruption without ambiguous ownership or artifacts | Passed for the bounded experimental route | [Recovery confirmation matrix](research-execution-confirmation.md), [backup and restore packet](durable-backup-restore.md) | Retain the bounded scope and the unproven disaster-recovery limits. |
| HTTP, SSE, CLI, and MCP expose one coherent retained artifact | Passed | [Client protocol](research-client-protocol.md), [conformance matrix](client-protocol-conformance.md), [recovered-journey PR #251](https://github.com/magnus919/groktocrawl-x/pull/251) | Confirm cross-client equality again at each remaining pilot checkpoint. |
| PostgreSQL can be the durable authority and pgvector can serve semantic search | Passed for the experimental deployment | [Storage evaluation](storage/pgvector-qdrant-evaluation.md), [application cutover packet](evidence/storage-vector-evaluation/2026-09-09-pgvector-serving-cutover/), [ADR-0079](../adr/0079-consolidate-retained-and-vector-storage-in-postgresql.md) | Keep Qdrant available until the operational rollback window passes; removal is separate work. |
| Migration to the candidate and rollback to the incumbent are rehearsed | Passed | [Migration and rollback packet](evidence/replacement-rehearsal/2026-09-11-migration-rollback/README.md) | Preserve the tested rollback path through the final decision. |
| Candidate operates over the required real-time window | Pending | [Pilot protocol](w9-operational-pilot-protocol.md), [tracked state](evidence/replacement-rehearsal/w9-pilot-state.json), [restart and checkpoint 0](evidence/replacement-rehearsal/2026-09-19-pilot-restart/README.md) | Run checkpoint 1 at or after `2026-09-22T02:19:40Z` and checkpoint 2 at or after `2026-09-26T02:19:40Z`. Require at least 30 successful representative operations and all pass rules. |
| Resource use fits ordinary operation on the home-lab host | Provisional pass at bounded scale | [Compatibility resource summary](evidence/replacement-rehearsal/2026-09-11-compatibility/resource-summary.json), [pilot protocol limits](w9-operational-pilot-protocol.md#limits) | Compare all three checkpoint snapshots and report any repeated material regression. Do not claim production capacity. |
| Operator burden is acceptable | Revised after a real failure | [Retained restart failure and correction](evidence/replacement-rehearsal/2026-09-19-pilot-restart/README.md), [operator runbook](../runbooks/experimental-replacement-candidate.md) | Confirm the guarded checkpoint runner works twice without manual reconstruction. Keep persistent private-file placement in the runbook. |
| Limits and residual risks are explicit | Passed for the preflight | [Pilot limits](w9-operational-pilot-protocol.md#limits), this report | Carry the limits into the final recommendation and create follow-up issues for any newly observed gap. |

## Architecture decisions

The final W9 PR must update status metadata and predecessor relationships without
rewriting decision history. Until the operational gate passes and the decider acts,
the following dispositions remain recommendations.

| ADR | Current status | Evidence-based preflight disposition | Remaining gate |
|---|---|---|---|
| [ADR-0073: compare research runtimes](../adr/0073-compare-research-runtimes-under-one-policy.md) | Proposed | **Revise and accept** the imperative reference as the default plus optional LangGraph for advanced workflows. The comparison found value in dynamic fan-out, durable interrupts, forks, and capability evolution, without making the graph the authority for application data. | Decider review; retain an explicit real-user/checkpoint operating gate before broad LangGraph use. |
| [ADR-0076: model-reviewed consolidated publications](../adr/0076-retain-model-reviewed-consolidated-publications.md) | Proposed | **Accept for the bounded experimental store.** The implementation retains explicit model provenance and fails closed on structural, support, conflict, freshness, and render-audit failures. | Decider review; no inference of human approval, public API, or production retention. |
| [ADR-0077: trusted consolidated bundle import](../adr/0077-trusted-consolidated-bundle-import.md) | Proposed | **Accept for trusted-server experimental import.** Exact validation, origin authority, bounded grants, idempotent receipts, and deletion/expiry behavior were exercised through the retained-artifact work. | Decider review; keep public and cross-trust import out of scope. |
| [ADR-0078: durable backup and artifact authority](../adr/0078-define-durable-research-backup-and-artifact-authority.md) | Proposed | **Revise and accept.** PostgreSQL is now the authoritative artifact store while Valkey owns bounded execution state, receipts, indexes, and deletion continuity. | Decider review; preserve the explicit absence of production disaster-recovery RPO/RTO proof. |
| [ADR-0079: consolidate storage in PostgreSQL](../adr/0079-consolidate-retained-and-vector-storage-in-postgresql.md) | Accepted | **Retain.** PostgreSQL authority and pgvector serving passed cutover and rollback evidence. | W9 operational window must pass before proposing removal of Qdrant from the experimental steady-state stack. |
| [ADR-0083: retain prose intake](../adr/0083-retain-prose-intake-over-universal-research-missions.md) | Proposed | **Accept.** Keep prose as the default and reject universal Research Mission normalization. Preserve smaller typed contracts for explicitly triggered workflows. | Decider review; any successor needs a narrower trigger and a new frozen comparison. |
| [ADR-0084: retain independent research roots](../adr/0084-retain-independent-research-roots-over-default-threads.md) | Proposed | **Accept.** Keep independent durable roots and construct explicit comparisons for follow-up research. Reject default accumulated-thread injection. | Decider review; any continuity feature must prevent stale-current leakage and prove value in a narrower trial. |
| [ADR-0085: independent semantic verification](../adr/0085-add-independent-semantic-verification-before-claim-publication.md) | Proposed | **Accept for experimental rollout.** The verifier removed the tested critical false accepts and missed contradictions without rejecting supported claims. | Decider review; live false-rejection, latency, case-mix, and rollback calibration remain required before stable-path promotion. |
| [ADR-0086: evidence-obligation continuation](../adr/0086-add-bounded-evidence-obligation-continuation.md) | Proposed | **Accept as an opt-in experiment.** Continue only for a named open obligation and stop on closure, zero gain, or the shared budget. Fixed retrieval remains the stable default. | Decider review; automatic obligation authoring and live retrieval yield remain unproven. |
| [ADR-0087: retain the generalist default](../adr/0087-retain-generalist-over-generic-specialist-fanout.md) | Proposed | **Accept.** Reject generic specialist fan-out and retain one research owner. Preserve the typed handoff for narrower task-specific experiments. | Decider review; future specialist work needs a calibrated router, a separable task class, and independent evaluation. |

## D1-D7 decision coverage

| Decision | Record | Preflight result |
|---|---|---|
| D1: execution, knowledge, and rendering boundaries | [ADR-0068](../adr/0068-separate-research-execution-knowledge-and-rendering.md) | Retain the accepted separation. |
| D2: versioned Knowledge IR and verification | [ADR-0069](../adr/0069-define-versioned-knowledge-and-verification.md) | Retain the accepted contract and independent verification boundary. |
| D3: evidence retention and vector storage | [ADR-0071](../adr/0071-store-research-evidence-independently-of-sessions.md), [ADR-0079](../adr/0079-consolidate-retained-and-vector-storage-in-postgresql.md) | Retain PostgreSQL authority and pgvector serving for the experiment; Qdrant exit remains conditional on W9. |
| D4: orchestration runtime | [ADR-0073](../adr/0073-compare-research-runtimes-under-one-policy.md) | Revise and accept the imperative default with optional advanced LangGraph use. |
| D5: durable execution ownership | [ADR-0074](../adr/0074-define-research-recovery-before-selecting-infrastructure.md), [ADR-0078](../adr/0078-define-durable-research-backup-and-artifact-authority.md) | Retain the bounded Valkey execution owner; revise ADR-0078 around PostgreSQL artifact authority. |
| D6: verified client protocols | [ADR-0072](../adr/0072-expose-verified-research-through-an-experimental-protocol.md) | Retain the accepted experimental protocol and bounded replay behavior. |
| D7: evaluation and adoption | [ADR-0070](../adr/0070-evaluate-research-policy-and-runtime-separately.md) | Retain the accepted evaluation discipline; final adoption awaits W9. |

## Final decision procedure

After the final eligible checkpoint:

1. Link both new checkpoint packets and update every pending row above.
2. Record whether the seven-day, 30-request, compatibility, artifact, storage,
   rollback, latency, and resource gates passed.
3. If a gate failed, preserve the failure, choose **revise** or **reject**, and
   open a focused follow-up issue for each missing proof.
4. If every gate passed, choose **adopt for the experimental fork**, apply the
   ADR dispositions above, and state the retained limits in the decision.
5. Synchronize the roadmap, experiment index, README, operator runbook, issues
   #311 and #312, milestone 8, umbrella issue #103, and the original plan issue
   #1 in the same change set.

The final report must distinguish three conclusions: fitness for continued use in
the experimental fork, readiness for this home-lab deployment, and any later
proposal to mainline. Evidence for the first two does not decide the third.
