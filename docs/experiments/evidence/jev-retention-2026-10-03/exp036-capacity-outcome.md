# EXP-036 direct scraper probe outcome (2026-10-03)

**Disposition: inconclusive; stopped before repeat sweeps.** The preregistered
34-URL pool was attempted once at caller widths 1, 3, and 5. All 102 attempts
returned `URLError`; none returned an HTTP response, source tier, or status.
The experiment therefore produced no successful-source latency or throughput
estimate. The helper used a literal internal-service host instead of the
candidate runtime `settings.scraper_url`; read-only diagnostics confirmed that
the configured target resolves while the helper literal returned DNS
`EAI_AGAIN` (errno -3). Historical receipts retained only `URLError`, so this
diagnostic identifies the likely setup error but cannot restore exact
per-attempt reasons.

The initial read-only preflight had agent and scraper health `ok`, zero active
research jobs, and available scraper tier metrics and aggregate CPU/memory
observations. Candidate revision remained fixed during the three passes. No
Jev or LLM calls were made. The direct internal scraper service route bypassed
the API route's semantic-indexing side effect. No result Markdown was captured
or published. The private, access-restricted ledger contains 102
candidate-bound attempt receipts, all with missing HTTP status and `URLError`.
Its receipt array has SHA-256
`c31dd126ee5fb82e64f8baecdf4ec1200f207b34e915af93e9604ee78ddfff52`. After
the attempt, I manually set the ledger `requests_completed` field to 102
without preserving its previous value. That provenance deviation is recorded
in the EXP-036-R1 transport addendum; the count here is independently derived
from receipt objects, and the current ledger will not be rewritten further.
The historical preflight did not capture a `scrape_calls_total` baseline, so
current cumulative service counters cannot establish whether these attempts
reached the service. No retained origin-request log proves per-attempt source
activity; the failed internal transport gives these attempts zero
source-quality credit.

The run stopped after the first pass at each width because every attempt failed
at the same transport error class. No retries or repeat passes were issued. The
30-minute and 204-request caps were not reached. Cold/warm behavior, successful
scrape capacity, end-to-end agent scheduling, progress, cancellation,
concurrent-agent behavior, and answer uplift remain unmeasured. The corrected
transport and canary-first protocol are recorded in the
[EXP-036-R1 transport addendum](../../jev-retention-capacity-2026-10-03-transport-addendum.md);
it requires independent review before further URL requests. Do not reinterpret
these failures as irrelevant or negative sources.
