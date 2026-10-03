# Current search baseline and remaining research questions

Reviewed 2026-10-03 against SlopSearX main
[`6bb683d4a9e154186c9d76af1b55e4faa24cf0e4`](https://github.com/magnus919/SlopSearX/tree/6bb683d4a9e154186c9d76af1b55e4faa24cf0e4)
and GroktoCrawl X main
[`9d3ffcfd97059e8c50b331533abdeaef3cf8360d`](https://github.com/magnus919/groktocrawl-x/tree/9d3ffcfd97059e8c50b331533abdeaef3cf8360d).
This is a source and evidence reconciliation, not a live deployment audit or a
new answer-quality comparison. The fork remains experimental.

## What upstream already provides

- **Semantic result ordering:** the shared search service uses optional Jev
  `jev-1.13.0` Score judgments over the first 40 deterministic candidates.
  Successful advice orders that pool across general and specialist tiers;
  unscored results retain deterministic order behind it. It reorders existing
  results rather than excluding them. Explicit engine scopes can still be
  reranked. Sensitive scopes are excluded, and unavailable advice falls back.
  The source-fusion `score` is not a Jev score or factual confidence.
  See [the upstream contract](https://github.com/magnus919/SlopSearX/blob/6bb683d4a9e154186c9d76af1b55e4faa24cf0e4/docs/JEV_RERANKING.md).
- **Scholarly work grouping before fusion and reranking:** recognized DOI,
  PMID, PMCID and arXiv identities, plus explicit version relations, collapse
  duplicate publications. Titles alone never establish identity. Each engine
  contributes once per grouped work; provenance and version information remain
  internally available. Group bounds or conflicting identifiers can decline
  a merge. Public output retains compatible Paper fields, not arbitrary
  internal member records. See [the grouping contract](https://github.com/magnus919/SlopSearX/blob/6bb683d4a9e154186c9d76af1b55e4faa24cf0e4/docs/SCHOLARLY_WORK_GROUPING.md).
- **GroktoCrawl integration already improved:** merged PR #406 preserves
  returned engine provenance and compatible scholarly fields through search
  results. Experimental research uses `limit=None` and admits every distinct
  returned URL under ADR-0092, subject to explicit caller budgets and operational
  guards. ADR-0090's optional post-scrape contribution filter is implemented;
  its retained pages reach synthesis in full. The keyless document projection
  still defaults to 8,000 characters and needs a late-passage control.

The owner's observation of materially better search is consistent with these
implemented changes. The older EXP-004/005 and EXP-016–023 studies remain historical
results on their recorded workloads and baselines. Their inconclusive outcomes
must not be generalized into a verdict against the current implementation.
The focused upstream run passed 71 reranking/grouping tests; its process exited
nonzero because the repository-wide 80% coverage gate was applied to this two-file
subset (29.77% overall coverage). This is not a full upstream CI pass.
Contract tests establish ordering, identity and fallback behavior; they do not
quantify current real-world answer improvement. Upstream's reranking guide also
explicitly limits its effectiveness claim.

## What remains for GroktoCrawl X

| Issue | Revised question | What we should not repeat |
|---|---|---|
| [#371](https://github.com/magnus919/groktocrawl-x/issues/371) | Does the existing post-scrape filter retain every useful contribution and improve synthesis on the improved search baseline? Include contradictions, complementary sources, late passages and duplicate versions. | Building another result-card reranker or treating retired acquisition quotas as the current baseline. |
| [#370](https://github.com/magnus919/groktocrawl-x/issues/370) | After the improved first pass, does another search close a specific evidence gap? Count distinct works and obligations, not engines or mirror URLs. | Re-evaluating upstream engine selection as if it were the research continuation decision. |
| [#372](https://github.com/magnus919/groktocrawl-x/issues/372) | Does the exact cited passage support the generated claim, including qualifiers, contradictions and version-specific claims? | Treating relevance, source agreement or a contribution score as proof of claim support. |
| [#373](https://github.com/magnus919/groktocrawl-x/issues/373) | Does a monitored page change matter to the user's stated intent? Distinguish actual content change from search reordering, grouping or representative changes. | Rebuilding upstream saved-search result-change reports. |

These remain follow-on studies, not unfinished W0–W13 requirements. Start with
#371's evidence-retention audit, then #372's exact support checks. Use the resulting
labeled obligations for #370; #373 can remain a separate monitoring study.

## Shared baseline requirements before new model calls

1. Record the deployed search revision separately from this reviewed source
   revision. Verify successful reranking through its explanation, and preserve
   final order, engine outcomes, cache state, available publication identifiers,
   publication/version notices and the actual returned result set. A configured
   key alone does not establish that advice was applied. Do not export keys or
   private deployment details.
2. Freeze real public search snapshots from that baseline and acquire every
   eligible distinct returned URL. Record every failure or exclusion. Preserve
   original result metadata and exact cited passages. Multiple engines or URLs
   identifying one paper are one work, not independent corroboration; do not
   invent absent work/version metadata or merge corrections by title.
3. Compare full acquired evidence without a contribution filter against the
   **existing** opt-in ADR-0090 filter on identical snapshots, model and synthesis
   instructions. Hold full-text projection constant to isolate filtering; assess
   the shipped keyless 8,000-character projection separately. The retired
   early-stop path is an optional historical negative control only.
4. Pre-label required contributions, contradictory evidence and source identity.
   Freeze calibration and validation sets. Report missed required passages,
   supported claim coverage, independent-work coverage, latency and separate
   search, scrape and Jev costs. Ranking position alone is insufficient.
5. Do not turn this reconciliation into a deployment, a new default, or an
   assumption that both installations already run the reviewed upstream code.
   Preserve the historical experiment packets and accepted ADR scope.
