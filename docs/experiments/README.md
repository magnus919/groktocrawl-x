# Experiment documentation guide

GroktoCrawl X is an experimental fork. Its results may inform a future replacement,
but they do not make this repository a replacement for mainline GroktoCrawl.

## Where to start

- [Research architecture plan](research-architecture.md): the current roadmap,
  workstream status, dependencies, and remaining gates.
- [ADR index](../adr/README.md): the current status of architecture decisions.
- [GitHub milestones](https://github.com/magnus919/groktocrawl-x/milestones): the
  live execution queue and issue ownership.

The roadmap tracker is the authority for current project status. The ADR index is
the authority for decision status. GitHub issues are the authority for individual
work items. If these disagree, update the overview documents; do not rewrite a
frozen protocol or completed evidence packet to make history look current.

## How the experiment records fit together

| Document | Purpose | Update policy |
|---|---|---|
| Research brief or analysis plan | Explains the question, comparison, and intended decision | Freeze before measurement; amend visibly if the design changes |
| Protocol or manifest | Pins inputs, bounds, revisions, and pass/fail rules | Treat as immutable once a run begins |
| Research log | Records execution, deviations, and operational observations | Append while work is active |
| Evidence packet | Preserves machine-checkable inputs and results | Never rewrite a completed packet; supersede it with a new run |
| Outcome or decision report | Explains what the evidence supports and what it does not | Correct factual errors visibly; use a successor for a new conclusion |
| ADR | Records an architecture decision and its consequences | Follow the immutability and successor rules in the ADR index |

## Current experiment areas

| Area | Primary documents | Current position |
|---|---|---|
| Architecture and baseline | [Roadmap](research-architecture.md), [W1 comparison](enterprise-evaluation/w1-comparison-outcome-2026-09-10.md) | Foundation complete; Candidate B rejected |
| Runtime orchestration | [Runtime comparison](runtime-comparison/report.md), [future-capability study](future-runtime-scenarios.md) | Imperative reference retained; LangGraph available for advanced workflows |
| Storage and recovery | [Storage evaluation](storage/pgvector-qdrant-evaluation.md), [ADR-0074](../adr/0074-define-research-recovery-before-selecting-infrastructure.md), [ADR-0079](../adr/0079-consolidate-retained-and-vector-storage-in-postgresql.md) | Recovery and pgvector decisions accepted for the experimental deployment |
| Replacement rehearsal | [Operational pilot protocol](w9-operational-pilot-protocol.md), [readiness preflight](w9-replacement-readiness-preflight.md), [evidence](evidence/replacement-rehearsal/) | Preflight matrix is complete; the remaining pilot checkpoints and final adoption decision remain open |
| Adaptive research policy | [W10 brief](adaptive-policy/w10-research-brief.md), [frozen protocol](adaptive-policy/w10-frozen-protocol.md) | Matched evaluation is running |
| SlopSearX research substrate | [W11 findings](slopsearx-substrate/w11-findings.md), [protocol](slopsearx-substrate/w11-protocol.md), [operator assessment](slopsearx-substrate/w11-operator-assessment.md) | Complete. Narrow adoption keeps HTTP search as default, rejects broad recorded continuation, and retains selected opt-in provenance and recovery contracts. |
| Research Mission contract | [W12.1 brief](research-mission/w12.1-experiment-brief.md), [protocol](research-mission/w12.1-protocol.md), [analysis plan](research-mission/w12.1-analysis-plan.md), [research log](research-mission/w12.1-research-log.md), [v1 freeze](research-mission/w12.1-freeze.json), [v2 freeze](research-mission/w12.1-freeze-v2.json) | Active. The v1 measured launch exceeded its failure guardrail and is excluded. The bounded v2 correction is frozen; matched control/treatment preflight is next. |
| Longitudinal Research Thread | [W12.2 brief](research-thread/w12.2-experiment-brief.md), [protocol](research-thread/w12.2-protocol.md), [research log](research-thread/w12.2-research-log.md), [v1 freeze](research-thread/w12.2-freeze.json), [v2 freeze](research-thread/w12.2-freeze-v2.json), [v3 freeze](research-thread/w12.2-freeze-v3.json), [evidence](evidence/research-thread/w12.2-final/00-index.md) | Complete. The tested default Research Thread is rejected: it was less accurate on fully observed pairs, slower, more token-intensive, and produced two stale-current leaks. Proposed ADR-0084 retains independent roots and explicit comparisons. |
| Independent claim verification | [W12.3 brief](claim-verification/w12.3-experiment-brief.md), [protocol](claim-verification/w12.3-protocol.md), [research log](claim-verification/w12.3-research-log.md), [v1 freeze](claim-verification/w12.3-freeze.json), [v2 freeze](claim-verification/w12.3-freeze-v2.json), [evidence](evidence/claim-verification/w12.3-final/00-index.md) | Complete. The bounded verifier passed every frozen gate in all three repetitions. Proposed ADR-0085 adds it as an experimental stage before source-bound claim publication. |
| TypeSafe Jev evidence routing | [Research brief](typesafe-jev/research-brief.md), [protocol](typesafe-jev/protocol.md), [research log](typesafe-jev/research-log.md), [exposed corpus](typesafe-jev/exposed-routing-corpus.json) | A bounded live technical smoke is complete on exposed synthetic cases. The adapter remains shadow-only and keyless-safe; no matched product-value measurement or adoption decision exists. |

Update this guide and the roadmap whenever an ADR changes state, a workstream
starts or finishes, or a new experiment becomes part of the replacement decision.
