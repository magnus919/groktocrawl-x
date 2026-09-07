# Recovery ownership contract status

The bounded contract fixture in `agent.experimental.recovery_contract` turns the
proposed ADR-0074 ownership rules into executable in-memory checks. It requires a
named execution owner, authoritative artifact store, monotonic fencing generation,
explicit retry/outbox/reconciliation owners, bounded lease/reclaim/heartbeat and
retry relationships, and an explicit at-least-once network-effect boundary.

The `RecoveryLedger` fixture covers stale-owner rejection, idempotent receipts,
conflicting receipts, cancellation/publication races, and exact receipt binding at
publication. It is a contract test only. It does not provide a durable lease,
process recovery, checkpoint persistence, provider reconciliation, or backup/restore
evidence. W5 remains open until the declared crash/cancel matrix is exercised
against a selected implementation and the resulting ADR decision is reviewed.

See [ADR-0074](../adr/0074-define-research-recovery-before-selecting-infrastructure.md),
the [execution confirmation matrix](research-execution-confirmation.md), and
[issue #111](https://github.com/magnus919/groktocrawl-x/issues/111).
