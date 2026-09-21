# TypeSafe Jev #360 research outcome

Decision: **do not ship or enable Jev passage triage in GroktoCrawl X from
this spike. Reject/defer the integration.** The decision owner is the
GroktoCrawl X maintainer; a later experiment would require a new decision.

The initial exposed synthetic smoke established that the pinned Jev endpoint
and shadow adapter can return typed decisions. It did not establish product
value. A separate matched synthetic comparison was frozen with preauthored
labels, a deterministic incumbent, a calibration/validation split, fixed
threshold-selection rules, and explicit quality, safety, latency, cost, and
failure gates. The run reached its predeclared operational-failure stop during
calibration. Validation did not run, and no triage threshold was selected.

This result supports a narrow conclusion: the candidate was **not ready to
ship under the declared experiment conditions**. It does not show whether
Jev would improve useful-evidence precision, preserve all needed or
contradictory passages, detect hostile text, improve supported answers or
citations, or perform well on real GroktoCrawl sources. Nor does it establish
that Jev is intrinsically unsuitable; limited diagnostic calls succeeded,
while the frozen batch failure remains unresolved. The scenario labels were
self-reviewed, not independent, as requested by the owner.

The keyless API, CLI, and MCP paths remain unchanged. The adapter is inert
experimental code and is not wired into user-visible execution; key presence
does not activate it. No SlopSearX code or behavior changed, and no Brave
Search call was part of the comparison. Existing deterministic safety and
provenance controls remain authoritative.

The raw ledger, model-specific performance details, frozen corpus, and
disagreement review are retained privately outside this public repository
pending publication review. Account-specific processing and publication
terms for real source text remain unverified; no private, authenticated,
personal, or sensitive source was submitted. No ADR selecting Jev is
proposed because no Jev architecture was adopted.

If the maintainer later opens a new spike, it should first diagnose the
batch transport failure and verify account-specific data terms. A fresh,
pre-registered real-source and end-to-end comparison—preferably with an
independent quality reviewer—would then be needed before reconsidering one
bounded use. This issue does not authorize that implementation or any
production activation.
