# Client protocol conformance status

The bounded contract fixture in `agent.experimental.client_protocol` defines one
application-owned `research/1` event model for status, SSE replay, CLI and MCP
projections. It rejects terminal payloads on progress events, requires an
accepted-first contiguous trace with exactly one terminal event, rejects foreign
or out-of-range cursors, and produces identical terminal projections for all three
client surfaces. The machine-readable traces under
`docs/experiments/client-protocol/golden/` freeze completed-conflict, failed-audit
and cancelled outcomes for cross-client parity checks.

The opt-in `GET /experimental/research/v1/capabilities` adapter now exposes this
boundary when `FEATURE_EXPERIMENTAL_RESEARCH=true`. A second opt-in gate,
`FEATURE_EXPERIMENTAL_RESEARCH_RUNS=true`, enables a fixture-backed process-local
run/status/cancel/event adapter plus exact in-memory artifact and evidence reads.
Its capabilities document advertises `fixture_run_adapter` and `process_local`
recovery, so it makes no durable execution or live-provider claim. Session
operations remain unavailable, the flags are off by default, and inherited `/v2`
routes are unchanged.

The tests cover completed, failed and cancelled terminal outcomes, duplicate replay
deduplication, sequence gaps, foreign cursors and no-terminal/terminal-order
violations. The run adapter is still a bounded fixture implementation, not
production research. W6 remains open until CLI/MCP journey parity, session
attachment, durable recovery, and the full authorization/deletion race matrix are
implemented and reviewed.

See [ADR-0072](../adr/0072-expose-verified-research-through-an-experimental-protocol.md),
the [proposed client protocol](research-client-protocol.md), and
[issue #112](https://github.com/magnus919/groktocrawl-x/issues/112).
