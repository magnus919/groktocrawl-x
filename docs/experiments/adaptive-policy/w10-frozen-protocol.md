# W10 bounded adaptive-query comparison protocol

Status: **corrected and refrozen before the valid execution**

## Cases and arms

Use all 24 frozen W8 cases as the reproducibility anchor and the 12 cases in
`w10-challenge-cases.json` as the challenge stratum. Report strata separately.
Counterbalance the five policies by case with seed `20260911`:

1. fixed query only;
2. W8-style unconstrained adaptive formulation;
3. one or two queries tied to a declared gap;
4. gap-tied queries that also pass the proposal gate;
5. proposal-gated queries plus marginal-value admission and deterministic stop.

The full policy executes its first admitted follow-up, acquires the bounded
results, and performs an interim evidence assessment. It stops before a second
follow-up when every gap is closed or that first follow-up produced no declared
evidence gain. Otherwise it may execute the second admitted follow-up. All arms,
including the full policy, receive a separate final blind assessment after
acquisition and backfill; the interim assessment is a policy input and never the
final score.

For each case, derive one seeded policy order and rotate it by one position per
repetition. Shuffle case order separately within each repetition. The resulting
work-order file is retained and hashed in the run manifest. A globally shuffled
ten-trial pilot was stopped and excluded after the data-science design audit
showed that it randomized order without counterbalancing policy position.

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

An initial 13-trial execution was stopped and excluded after a methodology audit
found that the implementation assessed evidence only after both follow-ups. It
therefore recorded a stop reason but could not stop between rounds. The excluded
tree is retained as `challenge-excluded-posthoc-stop` with SHA-256
`65bbf54573df711b9de6be7a728340c8412fcb2d0aa0a327c7b0c6afd1dc1949`.
The corrected implementation permits a third model call only for the full arm's
interim assessment and counts that call as policy cost.

A subsequent six-trial launch proved the sequential behavior but exposed an
accounting defect: a completed trial with no proposed follow-up retained the
nonterminal stop label `continue`. That launch is preserved and excluded as
`challenge-excluded-nonterminal-stop-reason` with SHA-256
`c7a1d2dff70fdbd54e1f8fa1b43d5cbdbf360819d50e27771d6ea8099b685db4`.
Every valid completed trial must instead record a terminal reason, including
fixed-query completion, planner-declared completion, no proposed follow-up, no
admitted proposal, exhausted proposals, an evidence-based stop, or a hard bound.

The first corrected one-case smoke reached that interim decision but the final
blind assessment exhausted the former 90-second ceiling. It is retained outside
the comparison as `pre-execution-sequential-stop-smoke` with SHA-256
`c748c01a83235951369a47375cec0c95f516a528e7376fb473493ceada0b6bc3`.
Because the additional assessment is required for the policy to observe its own
stopping condition, the valid execution uses a 180-second ceiling and retains
actual elapsed time and model-call count for every arm.

The repeated one-case smoke then completed in 72.153 seconds with two searches
and three model calls. The interim assessment found no material gain, the policy
stopped before dispatching the second proposed query, and the final blind
assessment completed successfully. Its private evidence tree is retained as
`pre-execution-sequential-stop-smoke-180s` with SHA-256
`6b49cec895009684b37c268004bd5967d60c48288520b7ee7f6c293bc147ce66`.

## Bounds and gates

Each case permits at most three searches, three planning/judging model calls, 20
results per search, eight admitted sources, and 180 elapsed seconds. A proposal
must name one gap, predict the evidence that closes it, differ materially from
prior query intent, and avoid broadening beyond the material claims.

A candidate is admitted only if acquired content supports or challenges a
material claim, improves authority or currency, resolves a contradiction, or
adds an independent publisher. Snippets and inaccessible pages remain logged but
cannot close a claim. Canonical duplicates and derivative reporting do not add
marginal value.

Stop when every material gap meets its case-specific closure rule; after a round
with no material claim, authority, currency, or contradiction gain; or at a hard
bound. Publisher independence remains a source-admission gain, but cannot alone
justify another query without evidence relevant to a declared gap. The stop
reason is computed from recorded state before a second follow-up is dispatched.
LangGraph carries the gap, proposal, decision, candidate
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

The runner writes a public query/candidate checkpoint and a separate private
acquisition checkpoint before grading. A grader or transport failure archives
both checkpoints, including excluded candidates, before the trial is retried.
Failure evidence is never treated as a policy outcome, but remains available for
the required manual adjudication and missing-data audit.

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

At launch, write immutable run metadata containing the exact 40-character source
commit and digests for the case file, freeze record, and runner. This record must
exist before the first network request so an interrupted run retains its identity.

The source and exclusion accounting, competing-hypothesis analysis, and durable
completion gate are defined in `w10-research-log.md`. Live execution uses the
same optional dependency as the earlier runtime studies,
`langgraph==0.6.11`, installed in an isolated experiment environment rather than
the production image.
