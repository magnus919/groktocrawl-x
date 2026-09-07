# Runtime comparison status

The W4 conformance seam is implemented in
`agent.experimental.runtime_comparison`. The imperative reference and the
framework-neutral graph-shaped candidate invoke the same `OperationSpec`,
`Budget`, `ExecutionLedger` and `ScriptResult` contracts. The graph candidate
adds dependency scheduling and deterministic receipt merging; it does not add a
framework dependency, persistence, recovery, or a second research policy.

The unit suite covers equivalent accounting, reverse branch completion with a
stable join, cancellation with unsettled reservations, cyclic-graph rejection
and over-budget receipt failure. These are conformance controls, not quality or
performance evidence.

The pinned [manifest](manifest.json) deliberately records zero paired
measurements and `baseline_frozen: false`. W1 has not yet approved the corpus,
reviewer, baseline bounds or uncertainty plan required by ADR-0073. Therefore no
runtime adoption decision is made here. The imperative implementation remains the
reference, the graph-shaped adapter remains an experimental candidate, and
paired cold/warm measurement is the next W4 gate after W1 baseline acceptance.
