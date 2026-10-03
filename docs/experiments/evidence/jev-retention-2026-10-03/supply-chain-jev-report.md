# Jev contribution retention: supply-chain search batch (2026-10-03)

**Disposition: revise / gather more evidence.** On this one frozen batch, the
existing ADR-0090 filter retained every page labeled as a possible material
contributor. The filter excluded nothing, so this is a retention result rather
than evidence that filtering improves answers. The keyless 8,000-character
projection separately clipped or omitted six labeled passage spans. Their
answer impact remains unmeasured.

## Frozen packet and acquisition

The query was “software supply chain provenance SLSA reproducible builds
attestations verification.” The captured SlopSearX response (`ssx-4ba02ef6`)
contained 20 returned results, was uncached, and marked partial. The response
had no Jev rerank explanation and no deployed search revision, so the packet
cannot establish that the reviewed upstream reranker was active. It is an
observed response from the supplied snapshot, not a deployment audit.

All 20 distinct result URLs were attempted once through the public scrape API.
All 20 returned nonempty Markdown, from 3,183 to 32,808 characters (327,605
characters total). Every scraper quality score was 1.0 and all four checks
(block detection, boilerplate, completeness, and volume) passed. These are
scrape-quality checks; they do not establish source authority or factual
correctness. The returned cards had no explicit DOI, PMID, PMCID, arXiv,
publication, work, or version identifiers. Exact content hashes showed 20
unique acquired pages; pages from the same standard or publisher still do not
count as independent corroboration.

The full input snapshot and pages remain in the owner’s private temporary
ledger. The committed label freeze stores source URLs, result/page hashes,
lengths, and offset spans, without page text. It is bound to protocol commit
`d46f852`, runner commit `9c29cd5`, and label commit `fc54186`.

## Jev assessment

Pinned `jev-1.13.0` assessed every complete page once, sequentially. All 20
calls returned valid scores. Scores ranged from 0.83 to 0.98 (median 0.97,
mean 0.958); all exceeded the existing 0.10 threshold. Thus the current rule
retained all 20 pages, including all 19 pages with a best-effort positive
contribution label. One page with an uncertain version-status claim was also
retained. There were no missed positive pages in this sample.

The 20 requests reported 79,886 input and 460 output tokens. Provider-reported
call latency had a median of 204 ms and a p95 of 226 ms; these are descriptive
per-call figures, not end-to-end filter latency or a concurrency benchmark.
The provider did not report a charge. Every page fit in one Jev chunk, so this
batch does not test the multiple-chunk maximum-score bias documented in the
protocol.

Labels were a single reviewer’s best-effort audit, not independent gold
judgments. They treat contribution, accuracy, source trust, and safety as
separate questions. The one uncertain status claim is preserved as uncertain;
its truth was not resolved here. Injection safety was not assessed.

## Missed-value and projection audit

All 28 labeled candidate-contribution spans are available in complete text and
remain present after the Jev filter because it removed no pages. In the
keyless 8,000-character projection, 22 spans are fully present, one is cut
partway through, and five begin after the projection. The five late spans are
on the [build-provenance explainer](https://www.encryptionconsulting.com/slsa-build-provenance-and-signing-in-ci-cd-pipelines/),
[verification walkthrough](https://www.systemshardening.com/articles/cicd/slsa-build-provenance/)
(two spans), [first-party draft specification](https://slsa.dev/spec/draft/build-provenance),
and [build-provenance guide](https://www.kusari.dev/learning-center/build-provenance/).
The partially clipped span is in [a provenance limits analysis](https://www.ostering.com/slsa-and-provenance/).
The draft specification’s labeled verification passage begins at character
20,890. These are pre-Jev, best-effort labels. They show projection loss in
this corpus, not that a generated answer would necessarily use every passage.

No synthesis calls were made: the full packet is about 80,000 tokens, and the
context limit for the available free-model alias was not verified. Since the
filter removed no source, the filter and score-only arms have the same source
set; score metadata could still affect synthesis. Answer quality, citation
support, and any such metadata effect therefore remain unmeasured.

## What this supports

Keep ADR-0090’s current experimental behavior unchanged. This batch supports
that the 0.10 rule did not discard any pre-labeled contribution in this
particular 20-result packet. It does not establish general recall, useful
source yield, answer improvement, safety, or production readiness. Continue
with a held-out batch that records the actual deployed search revision and
rerank explanation, independently reviews labels, and uses a synthesis model
with a verified context limit. Preserve the full-text and keyless-projection
comparisons as separate questions.

## Issue-scope disposition and evidence boundary

**Research-spike exit: revise; no new activation.** This result answers only a
narrow first-batch retention question: on one partial 20-result search snapshot,
19 pages received best-effort positive contribution labels and all 19 were
retained by the existing rule. It does not support general recall or an
answer-quality benefit. ADR-0090 remains opt-in and unchanged.

| Requested question | Evidence in this packet or repository | Disposition |
|---|---|---|
| Acquire every distinct result returned, without the retired local source quota | All 20 distinct URLs in this one partial snapshot were attempted and yielded Markdown. ADR-0092 and `tests/service/test_research_scrape_all.py` cover no-slice/deduplication and continuation after a mocked failure. | Demonstrated for this packet and deterministic code path; not a live 25–40-result capacity test. |
| Does the existing post-scrape filter retain useful contributions? | 19 positive and one uncertain page; all 20 were retained. There were no excluded pages, no independent label reviewer, and no labeled complementary or contradictory source. | Narrow recall observation only; negative-page behavior and broader recall remain untested here. |
| Does filtering improve answer synthesis on the current upstream search baseline? | The snapshot was partial, had no rerank explanation or deployed revision, and no synthesis call was made. Since nothing was excluded, the filtered and score-only source sets would be identical. ADR-0090 records an earlier complete-page replay where the unfiltered model ignored six obvious junk pages; that historical replay is not this baseline or a measured uplift. | Unanswered. Do not claim uplift or no uplift on the current baseline. |
| Does the keyless 8,000-character projection lose useful evidence? | Of 28 labeled candidate spans, 22 were present, one was partial, and five were beyond the prefix, including a frozen late-passage control. No synthesis was run. | Evidence of input projection loss in this corpus; answer impact is unmeasured. |
| Does acquisition remain acceptable at 25–40 sources under mixed latency/failure, cold/warm cache, cancellation, concurrent jobs, and progress reporting? | `tests/service/test_research_scrape_all.py` uses fake search/scrape clients and checks a 24-result case, mocked failure continuation, deduplication, and maximum five in flight. `agent-svc/agent/research/acquisition.py` and `discovery.py` implement bounded concurrency/timeouts/streaming. Separate run/cancellation tests cover lifecycle contracts. This packet reports 20 successful scrapes and sequential Jev calls, not end-to-end timings or multi-job load. | Implementation and contract coverage exist; target-width operational behavior and latency were not measured by this study. |
| Are chunking, threshold failures, version/work identity, source complementarity, contradictions, and safety adequately tested? | All pages fit one Jev chunk; every score exceeded 0.10; result cards had no explicit work/version identifiers; the label freeze has candidate-contribution spans only, including one uncertain status label. Injection/safety was not assessed. | Multi-chunk maximum-score bias, below-threshold recall, explicit duplicate-version handling, complementary/contradictory evidence, and injection behavior remain open. |

The smallest useful next **quality** comparison is one new, prospectively frozen
current-baseline batch, acquired without a local source quota, that includes
both a below-threshold page and independently reviewed required contribution
spans (otherwise the filter-removal contrast is not identified). On the exact
same acquired Markdown, prompt, synthesis model, and settings, compare full text
without Jev, full text with scores but no removal, the existing filter, and the
keyless 8k projection. Freeze the source/work/version labels and answer rubric
before Jev or synthesis outcomes; verify actual deployed reranking; explicitly
include complementary, contradictory, and post-8k evidence. Bound the run to one
batch and the already stated external-call budget. If the batch has no
below-threshold source or complete input exceeds a documented context limit,
report the comparison as non-identifying/blocked and stop rather than
manufacturing a contrast or silently truncating text. A subsequent read-only provider metadata lookup declared
`max_input_tokens=1,048,576` for alias `free`. This is a declaration, not an
empirically verified routed context limit; the report's synthesis outcome
remains unchanged, and no oversized synthesis request was made.

Treat the 25–40-source cold/warm, mixed-failure, cancellation, concurrent-job,
and progress measurements as separate operational prerequisites if adoption is
later considered. They are not part of the quality comparison above, and the
existing unit/lifecycle tests must not be presented as measured throughput or
capacity. No further provider calls, deployment, or activation are authorized
by this report.
