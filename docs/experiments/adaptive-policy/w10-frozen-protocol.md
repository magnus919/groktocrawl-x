# W10 bounded adaptive-query comparison protocol

Status: **frozen before execution**

## Cases and arms

Use all 24 frozen W8 cases as the reproducibility anchor and the 12 cases in
`w10-challenge-cases.json` as the challenge stratum. Report strata separately.
Counterbalance the five policies by case with seed `20260911`:

1. fixed query only;
2. W8-style unconstrained adaptive formulation;
3. one or two queries tied to a declared gap;
4. gap-tied queries that also pass the proposal gate;
5. proposal-gated queries plus marginal-value admission and deterministic stop.

The search provider, result cap, acquisition path, model family, prompts, and
case data are frozen. Technical execution is repeated three times. Model-created
query text may vary and every variant is retained.

The acquisition budget is eight pages. Fixed retrieval acquires its top eight.
Adaptive arms acquire the top four initial results and the top two novel results
from each executed follow-up; unused follow-up slots are backfilled in original
result order. All returned result metadata remains in the exclusion ledger. This
allocation was clarified after a pre-execution smoke test showed that grading up
to 24 full pages could not finish inside the already-frozen 90-second case bound;
the failed smoke record is retained and is not part of the comparison.

## Bounds and gates

Each case permits at most three searches, two planning/judging model calls, 20
results per search, eight admitted sources, and 90 elapsed seconds. A proposal
must name one gap, predict the evidence that closes it, differ materially from
prior query intent, and avoid broadening beyond the material claims.

A candidate is admitted only if acquired content supports or challenges a
material claim, improves authority or currency, resolves a contradiction, or
adds an independent publisher. Snippets and inaccessible pages remain logged but
cannot close a claim. Canonical duplicates and derivative reporting do not add
marginal value.

Stop when every material gap meets its case-specific closure rule; after a round
with no newly closed weighted gap and no authority, currency, contradiction, or
publisher-independence gain; or at a hard bound. The stop reason is computed from
recorded state. LangGraph carries the gap, proposal, decision, candidate
disposition, marginal value, and stop state; the deterministic policy owns the
decision.

Policy 5 replaces fixed retrieval for a named challenge type only if, in that
stratum and in at least two of three repetitions, it:

- improves weighted claim closure by at least 10 percentage points;
- leaves no more unsupported high-importance claims;
- keeps admitted-source precision within 5 percentage points of fixed retrieval;
- has at most 10% unnecessary executed queries after the last evidence gain;
- stays within every per-case work bound and has no higher failure rate.

Across the W8 anchor, it must not reduce weighted closure or precision by more
than two percentage points. If no policy clears all gates, fixed retrieval stays
the default and the result may still identify a narrower recovery policy.

## Evaluation and blindness

The primary unit is a declared claim gap. Weighted closure equals closed claim
weight divided by total claim weight. A source is useful when acquired content
materially supports or challenges at least one declared claim. Precision is
useful admitted sources divided by all admitted sources.

Grade relevance, source quality, and claim closure separately. Source quality
scores currency, relevance, authority, accuracy, and purpose from 0 to 2 each;
it does not substitute for claim support. Preserve contradictions. Record copied
or derivative relationships when visible.

Candidate records are randomized and arm/rank labels sealed before grading. A
frozen model grader scores acquired excerpts. Manually adjudicate all grader
schema failures, all high-importance closure disagreements, and a seeded 10%
sample. Report cluster-aware case distributions rather than treating source
sightings as independent observations.

## Sensitivity and missing data

Repeat the decision after removing unavailable sources, removing each challenge
case in turn, using equal claim weights, and counting ambiguous closure as open.
Exclude a case only when no arm can access evidence needed to score any declared
claim; preserve the case and unavailable candidates otherwise.

## Evidence package

Retain the environment manifest, query/proposal log, candidate and exclusion log,
claim-gap ledger, source-to-claim links, blind grades, sealed arm map, run-level
measurements, hypothesis analysis, sensitivities, and outcome. No essential
evidence may exist only in chat or an untracked temporary file.

The source and exclusion accounting, competing-hypothesis analysis, and durable
completion gate are defined in `w10-research-log.md`. Live execution uses the
same optional dependency as the earlier runtime studies,
`langgraph==0.6.11`, installed in an isolated experiment environment rather than
the production image.
