# W10 adaptive-query research log

Status: **template frozen before live execution**

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
