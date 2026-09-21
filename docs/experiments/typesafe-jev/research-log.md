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

- Confirm the account-specific legal/data-retention/publication terms before
  sending any non-synthetic GroktoCrawl content.
- Prepare a representative private frozen corpus and, if possible, obtain an
  independent labeler/adjudicator; absent that, retain the quality caveat.
- Freeze practical-effect, recall-loss, latency, cost, and provider-failure gates.
- Execute and retain the private matched comparison.
- Record adopt-one-use, revise, or reject/defer without inferring broader value.

## 2026-09-21 — bounded live technical smoke

- The owner supplied a TypeSafe key outside the public repository. Its local
  permissions were restricted to owner-only before use; the key was not printed,
  committed, or placed in a GroktoCrawl request body.
- A private technical-smoke freeze captured the pinned code/model/corpus, exact
  case order and digests, 12-call limit, two-second per-call timeout, two-way
  concurrency, no-retry policy, synthetic-only input class, and $1 ceiling.
- The exposed synthetic corpus was exercised once in shadow mode. Detailed
  provider receipts and the best-effort disagreement review remain in an
  owner-only local evidence directory outside Git. No Brave Search call or
  user-visible GroktoCrawl behavior change was involved.
- This was not the representative matched comparison required by #360. The
  assistant performed the preliminary review at the owner's request; it is not
  independent or blinded. No provider-specific performance figure is published
  here, and no confidence threshold or adoption decision follows from the smoke.
- The next study needs a revised route rubric, representative frozen cases,
  explicit incumbent arm, and predeclared quality/recall/cost gates. Any quality
  conclusion without a separate reviewer must be marked provisional.
