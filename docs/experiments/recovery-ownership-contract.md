# Recovery ownership contract status

The bounded contract fixture in `agent.experimental.recovery_contract` turns the
proposed ADR-0074 ownership rules into executable in-memory checks. It requires a
named execution owner, authoritative artifact store, monotonic fencing generation,
explicit retry/outbox/reconciliation owners, bounded lease/reclaim/heartbeat and
retry relationships, and an explicit at-least-once network-effect boundary.

The `RecoveryLedger` fixture covers stale-owner rejection, idempotent receipts,
conflicting receipts, cancellation/publication races, exact receipt binding at
publication, and provider ambiguity reconciliation for confirmed, absent, and
still-unknown outcomes (bounded evidence is tracked in [issue #143](https://github.com/magnus919/groktocrawl-x/issues/143)). The opt-in `DurableResearchLedger` merged in [PR #135](https://github.com/magnus919/groktocrawl-x/pull/135) adds a Valkey-backed bounded
implementation for admission, lease expiry/reclaim, monotonic fencing, persisted
cancellation, checkpoints, and terminal receipt commits with a recoverable projection
payload. Its tests exercise a new ledger
instance after lease loss, including stale-owner rejection, checkpoint persistence, terminal projection
persistence, and late cancellation.
This is still a recovery implementation slice, not a production deployment. The
experimental route now wires durable status recovery and persisted cancellation through
[PR #139](https://github.com/magnus919/groktocrawl-x/pull/139); bounded artifact bytes and
terminal event history are under review in [PR #142](https://github.com/magnus919/groktocrawl-x/pull/142). The durable route crash/cancel matrix is tracked in [issue #145](https://github.com/magnus919/groktocrawl-x/issues/145); backup/restore evidence and the infrastructure decision remain open. W5 remains open
until the declared crash/cancel matrix is exercised against the selected execution
path and the resulting ADR decision is reviewed.

See [ADR-0074](../adr/0074-define-research-recovery-before-selecting-infrastructure.md),
the [execution confirmation matrix](research-execution-confirmation.md), and
[issue #111](https://github.com/magnus919/groktocrawl-x/issues/111).
