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
specifier and the exact version used by this smoke run. It still
records zero paired measurements and `baseline_frozen: false`. W1 has not yet
approved the corpus, reviewer, baseline bounds or uncertainty plan required by
ADR-0073. Therefore no runtime adoption decision is made here. The imperative
implementation remains the reference, the LangGraph adapter remains an
experimental candidate, and paired cold/warm measurement is the next W4 gate
after W1 baseline acceptance.
