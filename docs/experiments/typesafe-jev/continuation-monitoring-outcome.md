# Jev continuation and saved-search monitoring run

Status: **execution incomplete; no semantic result is evaluable.** This is a
run-failure record, not a negative result for Jev or either proposed use.

## Frozen run

- Case-freeze commit: `0a967fa2bd782fd6b70bf6ee9dda3f20c75ae14d`
- Preregistered model: `jev-1.13.0`
- Frozen case packet SHA-256: `7d519f76c9a8f6318218a75490abc413b2390722192f9a01b61058eb11f842aa`
- Receipts SHA-256: `3af5c3500e6c48dc17b5de647146ee1e7262ad7cbdf122c21965c753729a9b8b`
- Private receipt path: `/private/tmp/gcx-jev-private-1003/receipts.json` (mode `0600`)
- Requests were sequential, with no retry or replacement call.

The runner produced `provider_failure` for all 10 attempted cases: #370 had 1
calibration and 3 validation cases; #373 had 3 synthetic calibration controls
and 3 public-revision validation cases. No case returned a valid Jev decision,
and no latency or token usage was recorded. Provider failures remain
**unevaluated**, never `irrelevant`, `no_search`, or `immaterial`.

The receipt omits raw proxy errors. A separate one-message, content-free
readiness probe returned `proxy_transport` with SSH return code 255 before any
provider response. The ten failed records had no elapsed-time field, consistent
with the same transport failure. No provider answers were received, so labels
remain blind. Those ten failed invocations are preserved as consumed attempts;
they are not relabeled as semantic model outcomes.

## What the run establishes

It establishes that this execution attempt did not deliver any usable model
judgments. It does not test decision quality, calibration, missed necessary
searches, unnecessary searches, intent sensitivity, notification noise, or
provider cost. No adoption, revision, or no-go decision follows from these
failures.

The #370 packet has no fresh search query or newly returned retrieval set; its
evaluator-only pool replays evidence from the existing search snapshot and
known public pages. If valid model execution is authorized later, report any
candidate-pool evidence gain separately from decision-only cases. The #373
validation material is three related project-authored documentation revisions,
not an independent or representative monitor corpus. The assistant labels are
best-effort assessments rather than independent gold.

## Validation

The runner's four focused tests pass with `pytest --no-cov`. Ruff check and
format checks pass. A privileged retry was rejected by the automatic approval
review because it would transmit frozen project-document contents through an
external Jev proxy without explicit destination-specific authorization; the
review also noted that the transport failure alone does not establish that no
data was sent. No retry was made. No application behavior, Hermes configuration, shared
roadmap, README, SlopSearX service, or mainline code changed.
