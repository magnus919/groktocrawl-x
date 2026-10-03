# EXP-036-R1 transport correction and canary preregistration

**Status:** pending independent protocol review; no new public URL requests have
been made under this addendum. The original EXP-036 receipts remain a separate,
zero-credit setup/transport outcome.

## Reconciliation of the first attempt

The original private ledger contains 102 receipt objects for 34 candidate IDs:
34 each at caller widths 1, 3, and 5; all are `URLError`, have no HTTP status,
and have no returned tier. The receipt-array SHA-256 is
`c31dd126ee5fb82e64f8baecdf4ec1200f207b34e915af93e9604ee78ddfff52`. After
the attempt, I manually set the ledger's `requests_completed` counter to this
count, without preserving the previous value. This is a provenance deviation.
This addendum independently derives the count from the receipt objects; the
existing ledger and receipts will not be rewritten further.

Read-only diagnostics inside the candidate agent used the same
`load_settings().scraper_url` base intended for `/scrape`. Health and OpenAPI
were reachable, and OpenAPI exposed `GET /health` and `POST /scrape`. The
configured transport target differed from the literal used by the first-run
helper. The configured host resolved; the helper's literal host produced DNS
`EAI_AGAIN` (errno -3) in the candidate agent. The historical receipts retain
only `URLError`, so this repeat diagnostic identifies the likely cause but
cannot retrofit per-request errno values. The scraper's current cumulative
counters are success=2059 and error=229; the original preflight did not capture
a `scrape_calls_total` baseline, so no delta is inferable. No direct origin-
request log is in the retained evidence. Since the helper failed while opening
its internal service transport, these attempts receive no source or scraper-
quality credit; exact per-attempt origin activity remains unverified.

## Corrected protocol

Use the exact privately retained 34-URL EXP-036 q1 pool, SHA-256
`9c903f589ef1c247aa7364b1769013032c1fb53088ebd98bd837d6d05ea9004d`. Do not
search for replacement URLs. The corrected helper must derive the internal
`/scrape` URL from the candidate agent's runtime `load_settings().scraper_url`;
it must not contain a literal service hostname. It may return only sanitized
status, failure/reason category, source tier, warning/degraded state, Markdown
length, elapsed time, and content digest. Never log or print the configured
base, credentials, URLs, titles, body text, or raw responses.

Create a new private run ledger; do not append to or replace the first ledger.
Start with a single canary: the first URL in frozen pool order, at caller width
1. Capture a private per-URL receipt. If the configured internal transport
fails before an HTTP response, record the exception class and sanitized reason
category and stop immediately. Do not retry the canary or issue other URLs. If
the service returns an HTTP response, that demonstrates the corrected internal
route is reachable; retain any source-level failure as an outcome and continue
only if health, revision, active-job, metrics, and resource checks remain
within the parent-reviewed baseline.

If the canary passes, continue the fixed pool at caller widths 1, 3, and 5,
then repeat each width once in that order. Count the canary as the first URL of
width 1/repeat 1. Maximum: 204 additional internal scraper requests, one
request per origin at a time, 70 seconds per request, 30 minutes total, no
retries. Do not call the repeat a warm-cache pass unless cache state is directly
observable. Stop on any unexpected internal transport failure, health failure
twice, candidate revision change, unrelated active job, HTTP 429, or time/request
bound. Preserve every attempted receipt and the stop reason.

Immediately before the canary and at each sweep boundary, read health,
OpenAPI route presence, scraper tier counters, `scrape_calls_total`, active
research job count, candidate revision, and aggregate CPU/memory through the
existing read-only path. Capture the same after the run. These are service-level
observations, not proof of general capacity or proof that unrelated traffic did
not occur. No `/v2/scrape`, search, Jev, LLM, job creation, indexing, cache
clearing, configuration change, deployment, or runtime modification is in
scope.

This run measures only direct scraper-service behavior over this returned
pool and candidate revision. It does not measure end-to-end agent scheduling,
progress, cancellation, two-job concurrency, answer uplift, or production
reliability. Those criteria remain unmeasured and cannot be inferred from this
bounded run.
