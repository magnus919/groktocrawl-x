# Frozen cardiac corpus: Jev question and request-shape study

## Registered protocol

Registered before new Jev calls on 2026-10-04 UTC. This is experimental development
and replay evidence, not fresh held-out validation or medical advice. The source
is the [upstream EXP-036 cardiac packet](https://github.com/magnus919/SlopSearX/blob/bc03032322d3f801454eb2f8119f705e9e1fd2cb/docs/experiments/evidence/EXP-036/q10-frozen.json).
The copied 44-card corpus has SHA-256
`1d472ef33f4a251711090aee3744bc4f75d3c44b90e88a13ab3797a72947f10c`.
No new search, Brave request, page fetch, deployment, or default change is authorized
by this protocol. The owner authorized these public cards to TypeSafe and permits
bounded Jev calls. Secrets and private transport details stay outside publication.

Three GPT-6 Luna agents reviewed question wording, corpus/labels, and comparison
design. Root checks their findings and owns the serial provider-call ledger.

### Questions and hypotheses

W0 preserves the previous ten-level Score wording and criteria. W1 independently
asks a four-level Score about substantive evidence visible in the card and a
three-option Choice about whether visible signals justify opening the source.
A promising bibliographic lead may deserve fetching while containing little
usable evidence. Neither judgment establishes unseen content, medical truth,
source novelty, or actual downstream benefit. The full trusted wording and
criteria are frozen in [contracts.json](evidence/cardiac-jev-replay-2026-10-04/contracts.json).

W0 versus W1 compares different model-plus-question contracts, not an isolated
wording ablation: scale, question count, and judgment dimensions also change.
Primary comparisons are within-contract order/cutoff/repeat stability. Quality
comparisons across contracts are descriptive rankings, never calibrated scores.

Hypotheses: separating retrieval priority from visible evidence reduces promotion
of bibliographic-only cards in an evidence-first ranking; scoring all 44 exposes
useful tail candidates when present; scores remain reasonably stable when
presentation order changes; singleton context may change judgments even with
identical per-card instructions and content. Each may be rejected or unresolved.

### Fixed matrix and budget

- 12 shared-state requests: first 40 versus all 44 × original/reverse/seeded
  shuffle × W0/W1. First-40 membership always means original `c0`–`c39`, even
  after reordering. Seed `91944`; first-40 shuffle projects the same all-44 shuffle.
- Four exact repeats: all-44 original and shuffle, once for each contract.
- Twelve singleton W1 requests: `c0,c6,c11,c13,c20,c21,c22,c25,c27,c29,c35,c43`.
  They preserve per-card instructions and content while changing surrounding
  state and sibling questions; this diagnoses a combined context/batching change.
- First pilot: all-44 original W0, all-44 original W1, singleton `c43`. Stop
  expansion if schema/model/membership validation fails. Pilot calls count
  toward the fixed 28-request ceiling; no automatic retries or replacement calls.
- One request in flight, 128,000 request bytes, 2,000,000 response bytes, 45-second
  transport deadline, 2,000,000 reported input tokens, 40-minute execution bound.
  A completed call can cross the token ceiling; that stops every subsequent call.
  Missing usage or unknown model identity prevents expansion. No production
  latency or queue-capacity claim from this private diagnostic transport.

Exact requests, membership and body hashes are in
[requests.json](evidence/cardiac-jev-replay-2026-10-04/requests.json).
The model is pinned to `jev-1.13.0`; requested and returned identities are recorded.
The [current provider API](https://docs.typesafe.ai/api) was checked before calls:
it supports typed Score/Choice and structured state. Failed `.md` documentation
fetches were supplemented by the live HTML API and primitive pages.

### Analysis frozen before calls

Reuse saved historical first-40/shared-state and whole-set/card-local receipts
as historical context, not fresh matched arms. New requests all use shared state
except explicitly identified singletons.

Sort primary rankings by descending evidence score, with numeric candidate ID
as the fixed tie break independent of presentation order. For W1 also report
lead-first ranking by `P(fetch)`, then evidence score, then numeric ID. No fitted
weights or action thresholds. Append the unscored tail in original order for
first-40 arms. No candidates are silently excluded or discarded.

Report nDCG@10 and useful@10 under both preserved assistant reference sets,
facet coverage, original-rank-41–44 exposure, empty-snippet promotion, and source
concentration. Labels are exploratory assistant judgments, not human gold.
They assess visible cards and cannot validate fetch-worth judgments. Report
rank/top-ten overlap and normalized-score shifts across input orders and exact
repeats, and paired singleton/shared-state shifts. Keep every failure in the
operational denominator. Record per-question validation errors, probabilities,
model identity, reported token usage, and observed transport/provider timing.
No inferential generalization across queries from this one exposed corpus.

For explanatory replay, compare engine/tier starting order and scored order;
never invent original per-engine ranks or call a reconstructed ordering RRF.
The six empty snippets remain empty. Optional policy replays use only saved
responses and require no new calls. There is no automatic adoption decision.

### Reproduction and delivery

The [inert runner](evidence/cardiac-jev-replay-2026-10-04/runner.py.txt) validates
all request hashes offline by default. Live execution requires explicit flags
and a separately supplied private transport; that transport is not committed.
An attempt receipt is persisted before dispatch, preventing accidental retries
of uncertain or invalid attempts. Public responses retain only judgment fields
and sanitized receipt metadata, excluding credentials and transport details.

Publish analysis, call receipts, a plain-English outcome, integrity hashes and a
reviewable PR in this experimental fork. No mainline or service behavior changes.
