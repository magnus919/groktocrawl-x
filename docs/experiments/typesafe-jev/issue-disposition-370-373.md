# Jev issue criteria disposition: #370 and #373

Status: **no adoption on the current evidence; both issue questions remain
open for a bounded follow-up or explicit maintainer no-go.** This is not a
claim that Jev is intrinsically unsuitable. Existing adaptive-search and
saved-search mechanisms are the baseline, and deterministic source identity
and change delivery remain authoritative.

## #370: continuation after first-pass evidence

The original four-case shadow screen exercised the existing `Choice` question
but did not dispatch searches. Its evaluator-only follow-up pool preserved
possible evidence for replay; merely having that pool is not an evidence-gain
measurement. The new eight-case staged Noul pilot exercised evidence
sufficiency, externally supplied gap hypotheses, and conditional public
addressability. Nineteen of 19 calls validated and all outputs aligned with
assistant-authored best-effort references. The second pilot also dispatched no
search and replayed no follow-up pool.

| Issue criterion | Evidence | Disposition |
|---|---|---|
| Freeze obligations and distinguish met, unmet, contradiction, and unanswerable | Original packet has one of each; new packet has sufficient, missing, and private/unresolvable cases | Partially exercised; no positive contradiction case in the staged pilot |
| Compare incumbent and Jev on the same evidence state | Original shadow screen did this descriptively on four cases; staged pilot records separate propositions, not a production incumbent comparison | Feasibility only |
| Replay a bounded follow-up set and measure distinct evidence gain separately from a recommendation | No replay executed in either completed report | Unmet |
| Measure missed necessary/unnecessary searches, obligation closure, answer/citation differences | No fresh query or answer arm; the staged pilot made no search decision | Unmet |
| Separate calibration and validation and review references independently | Original small split and staged assistant-authored references are not independent adjudication; staged pilot has no calibrated threshold | Insufficient for quality claims |
| Report latency, provider usage, and failure fallback | Captured for the two small shadow runs; no failure occurred in the staged run | Operational observations only |

Issue-level outcome: **do not adopt or integrate**. A next research pass can
reuse already acquired public SLSA/supply-chain pages as a deterministic,
evaluator-only second-pass replay, while first-pass Jev sees only its frozen
initial evidence. Use several external research obligations, include bounded
answerable gaps and a genuinely private/unresolvable control, and freeze the
query/result pools, span references, and expected evidence contribution
before any new call. Count newly dispatched searches as zero. This can assess
whether the replay pool would close an obligation; it cannot establish live
search quality, actual search cost savings, or retrieval uplift. The fresh
packet needs independent label review before execution and must keep future
evidence hidden from first-pass questions.

## #373: intent-significant page changes

The first six-case screen included three genuine public project-document
revision pairs, a synthetic boilerplate edit, a synthetic version-specific
change, and a synthetic fetch failure. The model marked the boilerplate
control immaterial and the version control material, but also returned
material for the failed-fetch control; that failure is unevaluated and cannot
be scored as a semantic change. It marked all three genuine project-authored
validation pairs material, matching best-effort assistant labels. These pairs
are topic- and author-context-selected.

| Issue criterion | Evidence | Disposition |
|---|---|---|
| Authoritative deterministic before/after identity | Frozen public Git blob hashes, diff identity, and exact changed ranges were retained | Covered for selected repository-document pairs |
| Real public pairs plus explicitly separate synthetic controls | Three genuine pairs and three synthetic controls | Small and selected; not representative |
| Factual updates, removals, contradictions, date/price/status changes | The public pairs are documentation changes; no coverage of date, price, status, or contradiction cases, and no dedicated removal stratum | Unmet coverage |
| Boilerplate, navigation/template, formatting churn | One synthetic boilerplate edit; no genuine navigation/template or formatting-only pair | Weak control coverage |
| Version-specific and ambiguous changes | One synthetic version-specific control; no ambiguous-intent/change case | Unmet coverage |
| Missing side/fetch failure behavior | One synthetic after-fetch failure; model returned material, correctly treated as unevaluated rather than a valid positive | Failure fallback must remain deterministic |
| Intent sensitivity and missed-material risk | Intents were present, but three related authored docs cannot estimate either risk | Unmeasured beyond examples |
| No notification suppression | Existing deterministic change signal remains authoritative; no implementation is enabled | Preserved |

Issue-level outcome: **no adoption or notification suppression**. The failure
control alone shows why a Jev response cannot replace source acquisition and
diff validation. Current examples support only a small shadow feasibility
screen. Additional cases should be frozen only if they can add independent
intents and underrepresented strata; otherwise maintain the no-go disposition
with the current deterministic path. No confidence calibration or reduction
in noisy notifications has been demonstrated.
