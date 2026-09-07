# W1 comparison packet proposal

Status: **draft for review; not frozen and not authorized for comparison runs**.

This is the next decision packet for the experimental fork. It turns the remaining
W1 work into a small set of choices instead of asking the maintainer to fill in
technical fields one at a time. The current preflight remains fail-closed until the
choices below are reviewed and written into the pinned manifest.

## Already decided

- **Research domain:** enterprise agentic engineering and software factories.
- **Inference:** local LiteLLM routing through the `local` alias.
- **External provider spend:** zero for this packet.
- **Human reviewer:** Magnus, with Hermes as a separate machine review; Hermes does
  not count as a second human.
- **Calibration:** the twelve exposed cases were reviewed and approved as a rubric
  check. They are not held-out cases and cannot produce the final quality score.
- **Runtime candidates:** the typed imperative reference and the optional LangGraph
  adapter pinned to the observed `0.6.11` version.
- **Safety rule:** the incumbent remains the reference until paired evidence supports
  a different decision. This fork remains experimental and makes no mainline
  replacement claim.

## Proposed test set

The current recommendation is **30 new, unique questions** divided evenly across
six topic families:

1. delivery and release authority;
2. secrets, permissions and identity;
3. exception and change governance;
4. ambiguous writes, recovery and side effects;
5. productivity, quality and cost measurement;
6. model/provider portability and evaluation controls.

The twelve existing calibration questions stay in the development/calibration
partition. They must not be copied into the held-out set. The held-out set should
contain six adverse or abstention cases (20%) and twenty-four ordinary answerable
cases. Each question needs a source bundle, an as-of date, fixed subquestions,
source lineage, and an access log showing who saw it before the run.

The held-out material should be sealed outside the tuning workspace after review.
If that isolation cannot be maintained, the resulting study will be labeled
exploratory rather than held-out.

## Proposed run order

1. Freeze the question/source packet and its digest.
2. Run the incumbent reference first, using the local model and the same source and
   token limits intended for the comparison.
3. Measure the incumbent's quality, latency, resource use, failures and model-call
   usage. These observations become the basis for proposed bounds; no target is
   invented in advance.
4. Review and freeze the bounds, randomization seed, hardware limits, repetition
   counts and uncertainty method.
5. Run the imperative reference and LangGraph under the same policy and failure
   schedule. Keep cold and warm runs separate.
6. Publish the results and update ADR-0073. The outcome can be retain, adopt,
   revise, or inconclusive.

The existing ADR minima remain proposals until this packet is accepted: at least
five stochastic trials per held-out question per arm and thirty paired repetitions
per runtime workload. Failed, timed-out and malformed outputs remain results; they
are not silently dropped.

## Decisions still needed before freezing

- approve or revise the 30-question shape and topic balance;
- identify the source curator and the isolation/sealing method;
- approve the exact hardware and service limits for the local run;
- approve the randomization seed and cold/warm cache policy;
- review the incumbent pilot results before setting regression bounds.

Nothing in this proposal changes `research-preflight.json`; unresolved fields remain
`null` until these decisions are made.
