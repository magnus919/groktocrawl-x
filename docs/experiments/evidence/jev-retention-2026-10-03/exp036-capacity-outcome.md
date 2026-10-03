# GroktoCrawl direct-scraper capacity outcome (GCX-CAP-036; 2026-10-03)

This GroktoCrawl study uses a 34-URL pool captured by SlopSearX EXP-036. The
study IDs refer to separate services and experiments. See the public source
card mapping in the [GCX-CAP-036-R1 transport addendum](../../jev-retention-capacity-2026-10-03-transport-addendum.md).

## Historical first attempt

The initial private ledger contains 102 attempt receipts for 34 candidates at
caller widths 1, 3, and 5. All returned `URLError`; none returned an HTTP
response, tier, or status. The helper used a literal internal-service host
instead of the candidate runtime `settings.scraper_url`; read-only diagnostics
showed the configured target resolving while the helper's literal host returned
DNS `EAI_AGAIN` (errno -3). The old receipts retained only `URLError`, so the
later diagnosis cannot recover per-request errno. The receipt array digest is
`c31dd126ee5fb82e64f8baecdf4ec1200f207b34e915af93e9604ee78ddfff52`. After the
attempt, the `requests_completed` ledger field was manually set to 102 without
preserving its earlier value. This provenance deviation is recorded, and the
historical artifacts were not rewritten further. These 102 attempts receive
zero source-quality credit.

## Corrected partial run R1

A new corrected run used the fixed pool and runtime-configured internal
`/scrape` route. Its canary returned HTTP 200. The first width-1 pass then
returned 20 more HTTP 200 responses before the next URL, public card `c1`
(pool rank 22, an arXiv PDF result), returned HTTP 502 (`http_error`, tier
`unknown`, no Markdown). R1 stopped immediately as preregistered: 22 starts and
22 result records total, 21 HTTP 200 and one HTTP 502. There was no retry or
replacement URL. Observed latency for the 21 HTTP 200 responses ranged from
86.7 to 7,259.9 ms (median 870.6 ms); this partial, rank-ordered prefix is not a
throughput or general-capacity estimate. The remaining pool and all repeat
widths were not attempted in R1.

The runner's early-stop path left its postflight field empty. A separate,
read-only postflight was therefore captured immediately afterward and retained
as a distinct mode-0600 artifact. Health was `ok`, there were zero active
research jobs, the candidate revision was unchanged, and tier metrics/resources
were available. Cumulative counters moved from success=2,062/error=229 at the
R1 baseline to success=2,083/error=230 after the read-only postflight. This
service-level movement is not attributable to this probe because other service
traffic may have occurred. The separate postflight capture is a documented
procedure deviation; it does not repair the missing field in the original
ledger.

Private artifact digests: append-only request receipts
`0f615bfa09f0c526d1940e8d34a4dac02c18fabd67b9d5ba26a2d10986219f7d`; R1
ledger `6f3039c75fd27afe21a8ea26c24b6a587fc9b15396b34fd08c8eab89edeba12c`;
separate postflight `2c58b476d97d22d2810185ead6f33f36c9a6dee4a43309a057ed0b1808f3e9d4`.
The private files contain sanitized request metadata and no complete page
text. The R1 direct-scraper experiment is incomplete and gets no broad capacity
claim.

## Registered continuation

[GCX-CAP-036-R2](../../jev-retention-capacity-2026-10-03-r2.md) prospectively
registers 170 starts over the same unfiltered frozen pool: width 1 once, width
3 twice, and width 5 twice. The R2 protocol treats HTTP statuses as per-page
outcomes, except HTTP 429 stops admission; transport, health, revision, and
unrelated-job stop rules remain. R2 has not started. Its outcome will be added
without overwriting R1 evidence.

Even if R2 completes, this direct scraper-service slice will not test
end-to-end agent scheduling, progress, cancellation, two concurrent jobs, or
synthesis/chunk complementarity and contradiction handling. Those adoption
criteria remain unmeasured. No Jev filter was activated and no deployment or
runtime configuration changed.
