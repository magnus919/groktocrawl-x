# W1 comparison packet proposal

Status: **approved for packet freeze; the comparison remains blocked until a
separately sealed packet and incumbent baseline review are complete**.

On 2026-09-08 Magnus Hedemark approved this packet proposal. The approval covers
the proposed question shape, topic balance, adverse-case minimum, local `local`
inference route, zero external provider spend, incumbent-first run order, and
fail-closed treatment of failed, timed-out, and malformed trials. It authorizes
the implementation agent to freeze the packet design and prepare the incumbent
baseline. It does not by itself establish held-out independence, authorize a
scored comparison, or make an adoption or production decision.

This is the next decision packet for the experimental fork. It turns the remaining
W1 work into a small set of choices instead of asking the maintainer to fill in
technical fields one at a time. The current preflight remains fail-closed until the
separately sealed packet, access record, and incumbent baseline review are written
into the pinned manifest.

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

## Implementation work before the comparison gate can open

- curate 30 new questions and their source bundles outside the tuning corpus;
- record the curator, every access event, sealing time, and the isolation method;
- validate the packet against the exposed corpus and retain the validation digest;
- record the local hardware/service limits, randomization seed, and cold/warm cache
  policy within the approved zero-spend envelope;
- run the incumbent reference first and bring its measured bounds back for review
  before any paired runtime or quality comparison.

`research-preflight.json` remains blocked until those implementation artifacts and
the baseline review exist. A digest alone cannot establish independence; the named
reviewer must still inspect the access and isolation record before the packet can be
marked eligible.
