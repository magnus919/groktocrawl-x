# TypeSafe Jev spike research log

## 2026-09-20 — preflight implementation

- Confirmed issue #360 remains an exploratory GroktoCrawl X spike.
- Recorded the separate SlopSearX engine-routing result as prior motivation only.
- Selected passage routing as the first candidate because it preserves the same
  constrained-choice shape without changing search-engine behavior.
- Added a direct HTTP adapter rather than an SDK dependency or `LLMClient` mode.
- Added strict response validation, bounded response size, HTTPS-only endpoint
  validation, a two-second default timeout, sanitized fallback reasons, and
  content-free receipts.
- Added deterministic fixtures for absent key, success, authentication,
  validation, rate limit, overload, generic provider failure, timeout, malformed
  JSON, incomplete answers, and inconsistent choice probabilities.
- Added twelve exposed synthetic calibration cases and a bounded runner.
- Verified the endpoint, typed response contract, pinned model, published limits,
  pricing, retry guidance, and public data-handling terms against current TypeSafe
  documentation; recorded them as vendor claims rather than measured evidence.
- The isolated checkout has no `TYPESAFE_API_KEY`; no live provider call was made.

## Open gates

- Obtain explicit authorization for a TypeSafe credential and spend ceiling.
- Complete the legal/data-retention/publication review described in issue #360.
- Assign an independent labeler/adjudicator and prepare the private frozen corpus.
- Freeze practical-effect, recall-loss, latency, cost, and provider-failure gates.
- Execute and retain the private matched comparison.
- Record adopt-one-use, revise, or reject/defer without inferring broader value.
