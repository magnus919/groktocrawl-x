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
boundary when `FEATURE_EXPERIMENTAL_RESEARCH=true`. It reports the contract and
golden-trace stage, an unadvertised recovery mode, and unavailable run/artifact/
evidence/session operations until their adapters are implemented. The flag is off
by default and inherited `/v2` routes are unchanged.

The tests cover completed, failed and cancelled terminal outcomes, duplicate replay
deduplication, sequence gaps, foreign cursors and no-terminal/terminal-order
violations. This is still a contract and golden-trace fixture, not a public route or
a claim that the existing API has changed. W6 remains open until actual API/CLI/MCP
adapters, authorization/deletion races and public-surface inventory are implemented
and reviewed.

See [ADR-0072](../adr/0072-expose-verified-research-through-an-experimental-protocol.md),
the [proposed client protocol](research-client-protocol.md), and
[issue #112](https://github.com/magnus919/groktocrawl-x/issues/112).
