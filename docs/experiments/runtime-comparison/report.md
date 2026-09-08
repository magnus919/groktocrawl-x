# Runtime comparison status

The W4 conformance seam is implemented in
`agent.experimental.runtime_comparison`. The imperative reference and the
optional `LangGraphRuntime` invoke the same `OperationSpec`, `Budget`,
`ExecutionLedger` and `ScriptResult` contracts. The adapter builds one
LangGraph node per operation, uses graph edges for dependencies, and serializes
ledger commits when independent branches finish concurrently. LangGraph is an
optional comparison dependency; it is not part of the production image and no
framework persistence or recovery is enabled. `GraphCandidateRuntime` remains
as a framework-neutral deterministic test double.

The unit suite covers equivalent accounting, reverse branch completion with a
stable join, cancellation with unsettled reservations, cyclic-graph rejection
and over-budget receipt failure. These are conformance controls, not quality or
performance evidence.

## Optional framework smoke evidence

On 2026-09-07, an isolated `uv run --with langgraph==0.6.11` environment ran
the W4 unit suite with **10 passed and 0 skipped**. The real LangGraph adapter
matched the imperative reference for a parallel branch/join case after
canonical operation-ID mapping, and cancellation preserved the unsettled
reservation without publishing a late output. The run used scripted local
callbacks, no provider spend, and no LangGraph checkpoint or store. It is a
framework conformance smoke result, not a paired performance measurement,
recovery proof, quality claim, or adoption decision.

The [manifest](manifest.json) records the optional LangGraph dependency
specifier and the exact version used by the smoke run. After W1 packet approval,
the first paired fixture measurement was recorded in
[`docs/experiments/evidence/runtime-comparison/2026-09-08/`](../evidence/runtime-comparison/2026-09-08/):
30 paired repetitions across three workloads in each first-run and repeated-state
lane, with zero conformance failures. LangGraph added measurable scheduling
overhead in this harness, including one retained first-run outlier, while both
adapters produced equivalent accounting and outputs.

The measurement is not a quality result, checkpoint/recovery proof, or production
selection. A second repeated measurement is recorded in
[`docs/experiments/evidence/runtime-comparison/2026-09-09/`](../evidence/runtime-comparison/2026-09-09/).
It uses a new fixed seed and repeats the same 30-per-workload cold/warm design;
all 360 additional records again conformed. The fresh-process cold lane shows
LangGraph graph-construction overhead (p50 181–194 ms versus 0.8–1.7 ms for the
imperative reference); the warm lane shows p50 3.3–5.1 ms versus 0.7–1.5 ms.
These are fixture observations, not end-to-end product bounds. `baseline_frozen`
remains false because the W1 numerical bounds and scoring protocol are still
unresolved. The imperative implementation remains the reference and LangGraph
remains an experimental candidate until ADR-0073 is decided with the remaining
W5/W6 evidence.
