# Narrow SlopSearX provenance adapter

Status: **implementation in progress; internal contract complete**

This adapter implements the narrow W11 adoption selected by
[ADR-0082](../adr/0082-delegate-bounded-retrieval-to-slopsearx.md). Ordinary
SlopSearX HTTP search remains the default. The adapter is internal and opt-in
under the named `retrieval-provenance-v1` profile.

## Authority boundary

GroktoCrawl continues to own the user's objective, evidence gaps, acquisition,
verification, synthesis, publication, and completion. The adapter accepts only
SlopSearX's retrieval handoff, idempotent receipt, and research-manifest
contracts. It never imports remote job status into GroktoCrawl's public artifact
model.

The retained reference has a versioned GroktoCrawl schema and contains only the
handoff contract/version, snapshot and result identities, receipt identity, and
a digest of the manifest. It sets `observations_verified` and `publishable` to
false. Later verification and publication gates cannot treat a receipt as proof
of a source claim.

## Profile and failure behavior

The profile requires `retrieval_receipts` and rejects deployments that also
grant broad jobs, research, staged-search, saved-search, or dependency-dossier
authority to this credential. The receipt workflow must report healthy before
use.

Every operation re-reads the result handoff before submitting a receipt. A
missing or expired snapshot, contract mismatch, unavailable receipt workflow,
receipt identity mismatch, or manifest omission fails visibly and returns no
reference. Receipt keys are derived from the GroktoCrawl owner, SlopSearX result
identity, and exact capture observation, so retry after timeout or restart
replays the same mutation.

## Remaining production slice

The next implementation milestone supplies the authenticated MCP transport,
bounded durable reference storage, deployment configuration, aggregate health,
retention cleanup, and rollback switch. Those pieces must pass an isolated live
recovery check before issue #327 can close. Disabling the profile must leave
ordinary HTTP search and existing deployments unchanged.

The contract and recovery behavior are based on the [W11 provenance and
recovery evidence](evidence/slopsearx-substrate/2026-09-11-isolated-provenance/)
and the final [W11 findings](slopsearx-substrate/w11-findings.md).
