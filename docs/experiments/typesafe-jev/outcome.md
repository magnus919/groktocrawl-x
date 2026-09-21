# TypeSafe Jev #360 research outcome

Decision: **do not ship or enable Jev passage triage in GroktoCrawl X from
this spike. Reject/defer the integration.** The decision owner is the
GroktoCrawl X maintainer; a later experiment would require a new decision.

The original closure of #360 was premature. Its first frozen synthetic batch
stopped during calibration because provider calls failed; validation never
ran. That was an operational hiccup, not evidence that Jev lacked product
value. The issue was reopened to diagnose and finish a bounded evaluation.

Direct and adapter diagnostics subsequently succeeded. A second, separately
frozen synthetic batch completed validation and selected a conservative
shadow-triage threshold. That threshold was then held fixed for a separately
frozen comparison using excerpts from first-party, public GroktoCrawl X
documentation. Both repetitions completed without fallback. The policy
retained every passage labeled necessary, including the premise-challenging
ones, and removed some unnecessary material. It nevertheless missed the
predeclared minimum useful-evidence precision improvement. This completed
real-public-source value screen, **not the earlier provider failure**, is the
basis of the no-ship decision.

The document pool was hand-selected from one technical repository, and its
labels were reviewed by the assistant rather than an independent or blinded
reviewer. The comparison measured passage retention, not final-answer quality
or citation accuracy. The first batch failure's cause remains unresolved;
later successful runs show only that it was not a permanent outage. This
outcome does not establish that Jev is intrinsically unsuitable, or speak to
its separate search-engine-routing use in SlopSearX. The spike's stop rule
does not justify expanding to reranking, citation checking, or extraction
adjudication on these results.

The keyless API, CLI, and MCP paths remain unchanged. The adapter is inert
experimental code and is not wired into user-visible execution; key presence
does not activate it. No SlopSearX code or behavior changed, and no Brave
Search call was part of the comparison. Existing deterministic safety and
provenance controls remain authoritative.

The frozen corpora, labels, provider-specific measurements, raw ledgers, and
disagreement review are retained privately outside this public repository
pending publication review. Only public, low-risk first-party documentation
was submitted under the account's published terms; no private,
authenticated, personal, or sensitive source was sent. No ADR selecting Jev
is proposed because no Jev architecture was adopted.
