# TypeSafe Jev #360 interim research outcome

Status: **research continues; do not ship or enable Jev passage triage yet.**
There is no final adopt/reject decision from #360. The experimental adapter
remains shadow-only and inert in user-visible paths.

The original closure of #360 was premature. Its first frozen synthetic batch
stopped during calibration because provider calls failed; validation never
ran. That was an operational hiccup, not evidence that Jev lacked product
value. The issue was reopened to diagnose and finish a bounded evaluation.

Direct and adapter diagnostics subsequently succeeded. A second, separately
frozen synthetic batch completed validation and selected a conservative
shadow-triage threshold. Applying that threshold to public first-party
GroktoCrawl X documentation preserved all passages labeled necessary but
missed the predeclared minimum useful-evidence precision improvement. That
was a valid result for **that threshold**, not a final judgment about Jev.
The threshold came from synthetic cases and a conservative tie-break; it was
not calibrated on real GroktoCrawl passages.

The owner pointed out that Jev returns continuous confidence signals and
that the cutoff should be learned from real-model behavior. A further set
of public first-party passages was labeled before live calls and run twice.
Together, the two real-document sets now form exploratory calibration data.
A less restrictive candidate cutoff retained all passages labeled necessary
while filtering more of those labeled unnecessary in both sets. Because that
cutoff was nominated after inspecting these data, **neither set is an unbiased
validation of it**. The numbers are model scores, not demonstrated
probabilities that a source is trustworthy. Source authenticity and
provenance remain separate deterministic responsibilities.

The document pools were hand-selected from one technical repository, and
labels were reviewed by the assistant rather than an independent or blinded
reviewer. They measure passage retention, not final-answer quality or
citation accuracy. The first batch failure's cause remains unresolved;
later successful runs show only that it was not a permanent outage. These
results do not establish broad-web generalization or speak to Jev's separate
search-engine-routing role in SlopSearX. Keep the spike focused on calibrated
passage triage before considering another Jev role.

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
is proposed because no Jev architecture has been adopted. The next decision
requires a separately frozen validation set and, if its passage-level gates
hold, an end-to-end answer/citation comparison. Do not reuse the calibration
sets as if they were held out.
