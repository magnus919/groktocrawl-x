# Local similarity relevance evaluation

## Decision

Issue #350 blocks an unconditional replacement recommendation because local
vector similarity can return complete but weakly related results. This bounded
evaluation tests changes at the retrieval boundary while keeping the public
endpoint and vector-store provider stable.

## Frozen cases

| Query page | Relevant result families |
|---|---|
| Python success stories | Python use, adoption, case studies, and closely related Python material |
| Python free-threading extensions | Python free-threading guidance and implementation documentation |
| Descript editor interface | Descript editing, scenes, layouts, sequences, and editor guidance |
| Agentic software factory guide | Agentic software factories, coding agents, and repository automation |
| OpenAI Codex product page | Codex documentation, repositories, product guidance, and workflows |

The query URL itself is always excluded. Reviewers grade each returned URL as
relevant (2), related but weak (1), or irrelevant (0). A case with no defensible
local match should eventually support abstention instead of forced results.

## Compared policies

1. Baseline: return cosine-similarity order from the active vector store.
2. Candidate: retrieve up to five times the requested result count (bounded at
   50), then cross-encode title plus excerpt against the query-page
   representation and return the requested top-k.

The candidate preserves vector score, raw rank, reranked rank, reranker score,
candidate-pool size, and ranking method so failures remain diagnosable. If the
reranker is unavailable or returns no usable positions, the endpoint falls back
to vector order.

## Metrics and promotion gate

Record nDCG@5, precision@3, reciprocal rank of the first relevant result,
irrelevant-result rate, and end-to-end latency for every case. Promote the
candidate only when it improves mean nDCG@5 and precision@3, causes no material
per-case regression, and keeps the live endpoint inside its existing timeout.

Do not tune a score threshold from these five cases. If reranking passes, collect
a larger labeled packet before choosing abstention thresholds, representation
changes, hybrid retrieval, or another embedding model.

## Rollback

Revert the agent-service change to restore cosine ordering. No schema, vector,
or retained-artifact migration is involved.

## First execution result

The first live candidate retrieved up to 50 documents and submitted them to the
shared cross-encoder. The rerank exceeded the 60-second semantic-client timeout,
fell back to vector order after roughly 95 seconds end to end, and left following
vector searches waiting behind the serialized inference lane. The deployment was
rolled back immediately.

This variant is rejected. A future reranking experiment must first prove a much
smaller candidate pool and bounded document representation directly against the
semantic service without affecting the serving endpoint. Until then, the
production-shaped candidate retains cosine ordering and issue #350 remains open.

## Second execution result

A second candidate limited reranking to ten short title-and-excerpt pairs. A
direct semantic-service probe completed in roughly 6.5 seconds, but the full
serving path took roughly 42.7 seconds and promoted generic Python navigation
pages. It removed one clearly unrelated result but did not produce enough
relevance improvement to justify the latency. This variant was rejected and was
not merged.

## Current representation experiment

The two rejected rerankers show that query-time model work is the wrong first
intervention. The current cosine index embeds the first 2,000 content characters
and exposes the first 500 characters as its excerpt. On documentation pages,
those ranges can be dominated by navigation. Some acquired pages can also begin
with prompt-like boilerplate. Both weaken the stored representation before
retrieval begins.

The next candidate therefore keeps plain cosine retrieval and changes indexing
only:

1. prepend the acquired title;
2. remove navigation, link-heavy menu blocks, basic Markdown markup, and
   prompt-like blocks from the bounded embedding text;
3. store the same cleaned text as the result excerpt; and
4. expose a `clean-v1` representation version in similarity provenance.

Before this candidate was installed, the five frozen cases were recorded
against revision `99481a1a`. Four returned results in 9.6–16.1 seconds; the Codex
case returned no local matches in 0.7 seconds. The Python tutorial case returned
four pages titled “Navigation,” the Python free-threading case returned two, and
the other cases mixed strong matches with unrelated pages. This is the baseline
for the representation comparison.

Promote `clean-v1` only if freshly reindexed evaluation pages improve the human
relevance grades without adding material request latency or causing a per-case
regression. A page that cannot produce useful cleaned text falls back to its
title, then its URL, so indexing never submits an empty embedding input.

## Representation rollback

Restore the prior revision and reindex the affected evaluation pages to recreate
their original raw-leading-content representations. No database schema change
or vector-store migration is required.
