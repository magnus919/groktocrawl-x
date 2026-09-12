# W10 adaptive-query research log

Status: **live study in progress; protocol remains frozen**

## 2026-09-12 — completed measurement and independent adjudication

The refrozen challenge produced 180 valid completed trials. The matched W8
anchor produced 360 valid completed trials after a resumable recovery pass
repaired 15 identities interrupted by model-gateway transport failures. The
original failed attempts remain separately preserved for the missing-data
audit; they were not reclassified as policy outcomes. Both run validators pass,
and the combined summary and blinded adjudication packet are complete.

Independent adjudication is pinned to the Hermes `luna` model alias. Every
observation uses a fresh one-shot session, the full rubric must validate before
its private checkpoint is written, and malformed attempts remain preserved for
the audit. Four disjoint execution lanes reduce elapsed time without changing
the unit of review. Their identity sets were checked against the original
packet: all 4,487 observations occur exactly once, with no omission or overlap.
The shared checkpoints remain resumable, and no intermediate judgment or
private evidence is used to infer the outcome before the complete record is
assembled and validated.

## 2026-09-11 — independent-review handoff smoke

The adjudication handoff now sends each blinded observation to a fresh Hermes
one-shot through a private query file. The runner disables repository rules and
outside tools for the review, treats supplied excerpts as untrusted evidence,
validates the complete rubric before checkpointing, removes the prompt file after
the call, and resumes already completed observations without another model call.

A one-item synthetic source-grade smoke completed through the installed Hermes
CLI. Its response contained exactly the required fields, all five quality scores
were within the frozen zero-to-two range, and no prompt file remained. The smoke
contains no experiment outcome and does not enter the W10 analysis.

## 2026-09-11 — adjudication recording gate

The completed-run handoff already builds a blinded packet containing the seeded
10% source sample and every required disagreement. It did not define a strict
way to record the independent review. A new validator now requires complete,
one-to-one judgments, agent-review and blinding disclosures, bounded rubric
values, and exact packet/manifest hashes before producing a public result.
Private excerpts and written rationales do not enter the public artifact.

This closes the mechanical handoff from model grades to agent adjudication. It
does not prejudge any observation and does not modify the frozen runner,
measurement cases, prompts, or model grades.

The downstream analysis applies reviewed source-usefulness and claim-closure
judgments only to their selected observations, reports model/agent agreement by
rubric dimension and selection reason, and recomputes the complete decision as
an adjudication sensitivity. The frozen model-graded result remains the primary
analysis. A changed sensitivity decision must be reported rather than silently
rewriting the primary result.

The public accounting builder closes the remaining dossier handoff without
copying private research material into Git. It counts every trial, executed
query, candidate, search sighting, acquisition, admission, exclusion,
source-to-claim link, proposal disposition, and terminal stop reason. It also
binds the private acquisition files through a canonical hash manifest and
reports min/median/max variation by policy and challenge type. The builder
fails closed when the frozen summary, record counts, private-file counts, or
required disposition fields do not agree.

This is the durable accounting record for the W10 study. The runner fills the
machine-readable records; the final synthesis updates the tables below. A study
run is incomplete while any retained or rejected candidate lacks a recorded
disposition.

## Search history

Each trial record preserves the case, query text, policy, repetition, purpose,
target gap, elapsed time, and result count. The run manifest binds those records
to the frozen case file, seed, environment, and dependency versions.

## Source and preservation ledger

For every candidate URL, retain:

- title, canonical URL, publisher identity, and access time;
- acquisition status and content digest;
- separate currency, relevance, authority, accuracy, and purpose scores;
- material claims supported or challenged and the resulting gap disposition;
- canonical, derivative, or publisher relationship;
- admission or exclusion decision with its reason.

Acquired excerpts are kept in the private evidence packet because redistributing
source text may be inappropriate. Tracked trial records retain hashes, judgments,
provenance, and source-to-claim links. Inaccessible, duplicate, derivative,
irrelevant, and out-of-scope sources remain in the ledger with an exclusion
reason.

## Competing-hypothesis matrix

The final report evaluates every evidence item across H0-H5 rather than counting
only evidence that favors adaptation.

| Evidence item | H0 fixed sufficient | H1 query drift | H2 weak admission | H3 late stopping | H4 challenge-specific benefit | H5 grading sensitivity |
|---|---|---|---|---|---|---|
| Primary metrics by case and repetition | Pending | Pending | Pending | Pending | Pending | Pending |
| Query proposal and gate decisions | Pending | Pending | Pending | Pending | Pending | Pending |
| Candidate exclusions and marginal value | Pending | Pending | Pending | Pending | Pending | Pending |
| Stop reasons and work bounds | Pending | Pending | Pending | Pending | Pending | Pending |
| Blind grades and adjudications | Pending | Pending | Pending | Pending | Pending | Pending |
| Leave-one-case-out and missing-data sensitivities | Pending | Pending | Pending | Pending | Pending | Pending |

Use `consistent`, `inconsistent`, or `not diagnostic` in the completed matrix.
Prefer the hypothesis with the fewest important inconsistencies. Identify any
linchpin evidence whose removal changes the decision.

## Method audit and exclusions

Each interrupted or invalid execution remains in the private evidence tree with
its digest and reason for exclusion. A timeout is treated as an interruption,
not an outcome. The study resumes only after the partial evidence is inspected,
the defect is reproduced, and a focused regression test plus the run validator
close the affected evidence edge. The frozen protocol lists every excluded tree,
including the stale-gap proposal-gate launch found during the full
research-methodology audit.

The independent validator must prove the policy's central decision invariants
from retained records. It may not infer correctness merely because the same
runner produced the records. This includes rejecting any admitted proposal whose
target gap was already closed in the preserved initial assessment.

For sequential full-policy trials, preserve both the interim assessment used to
decide whether another query should run and the separate final blind assessment
used for outcome scoring. Record and adjudicate disagreements rather than
silently replacing one judgment with the other.

The launch retained as `challenge-excluded-unpreserved-final-assessment` failed
two final candidate-cardinality checks after 27 attempted trials. It is excluded
because the exact invalid assessments were not recoverable. The corrected
runner checkpoints every returned assessment and its response receipt before
candidate and gap coverage validation; the run validator checks this failure
path independently.

The corrected runner completed the one-case fixed-policy
`pre-execution-final-assessment-preservation-smoke` against the pinned
candidate and local model route. The independent validator found no issues.
Its five-file evidence manifest has SHA-256
`ab71da5cacc847021bbfcc94e80fbc8f813eabaf303a2176905f0c1203171e65`.

The first full relaunch was stopped during its first trial after detecting that
the launcher's full source-revision value did not match the checked-out commit.
The six-file partial evidence tree is retained as
`challenge-excluded-launch-commit-typo`, SHA-256
`89ed1c5c8c37133395189106417cdfc011979b460c5ed66e8793a86d9ca7145d`,
and is ineligible for analysis.

The following clean launch reached 21 completed trials and three final
assessment failures before it was stopped. Every failure returned eight grades
but duplicated candidate IDs, omitting between one and five expected IDs. The
new checkpoints preserved each exact response and receipt, which made the
shared failure mechanism observable. The run is retained and excluded as
`challenge-excluded-array-assessment-identity`; its 57-file canonical manifest
has SHA-256
`d3e96107945173839d3489c846f5f93cfacf2744da105c9d556218c5d6c1ebb6`.

The assessment wire schema now represents candidate and gap IDs as required
object keys rather than enum-valued array fields. This makes missing or repeated
identity structurally impossible when strict schema enforcement succeeds. The
runner retains the wire response before validation and converts it to the same
list-shaped analysis record afterward. No repair call or post-hoc grade mapping
was added.

The keyed schema completed a live smoke on the freshness gap-policy combination
that had failed in both earlier full launches. The independent validator found
no issues. The retained five-file evidence tree
`pre-execution-keyed-assessment-smoke` has canonical manifest SHA-256
`2258d1d76015393a14482d27ee1a7055f8a716f04f21db1a3a7c63b0f19f4366`.

## Completion gate

- [ ] Every executed search appears in the query log.
- [ ] Every candidate appears in the source ledger, including exclusions.
- [ ] Every retained source is linked to a claim or recorded research purpose.
- [ ] Blind grades and manual adjudications are durable and discoverable.
- [ ] The hypothesis matrix and all required sensitivity analyses are complete.
- [ ] Environment, software, model, and dataset digests permit reproduction.
- [ ] No essential evidence exists only in chat or an untracked temporary file.
- [ ] The boundary measures and four-way decision form in
  `w10-analysis-plan.md` are complete.

## Final artifact pyramid

The completed study is published under
`docs/experiments/evidence/adaptive-policy/w10-final/` with progressive detail:

- `00-index.md` contains navigation and provenance only;
- `01-summary/findings.md` gives the decision and user implications;
- `02-analysis/` separates policy effects, source quality, sensitivity,
  LangGraph behavior, and limitations;
- flat `03-dossiers/` files contain methodology, run manifests, source and
  exclusion ledgers, adjudications, and raw machine-readable results.

Every Markdown artifact ends with a `SOURCES` navigation section. The tracked
Layer 3 material links by digest to private acquired excerpts retained on the
experiment host, without republishing source bodies. The roadmap and ADR link to
the Layer 1 finding rather than duplicating its analysis.
