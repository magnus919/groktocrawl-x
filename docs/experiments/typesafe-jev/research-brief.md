# TypeSafe Jev evidence-router research brief

- Tracking issue: [#360](https://github.com/magnus919/groktocrawl-x/issues/360)
- Status: **research closed — do not ship Jev passage triage from this spike**
- Scope: GroktoCrawl X experimental research path only
- Decision owner: Magnus Hedemark

## Decision

Determine whether Jev earns one bounded role as an optional shadow decision layer
around GroktoCrawl evidence. This spike is not a commitment to TypeSafe, a stable
provider abstraction, production traffic, or mainline behavior.

Experience from a separate SlopSearX experiment suggests that Jev can route a query
among fixed search-engine choices. That observation motivates the shape of this
trial but is not GroktoCrawl evidence and does not authorize SlopSearX changes here.
The first GroktoCrawl treatment routes one acquired passage to `evidence`,
`conflict`, `irrelevant`, `unsafe`, or `uncertain` before synthesis.

## User-visible problem

Similarity and extraction success do not establish that a passage is useful or
safe evidence. A near match can be irrelevant, a contradiction can be wrongly
dropped, and a retrieved page can contain instructions aimed at the synthesizing
model. General-purpose generation can classify these cases, but adds a broad
provider contract to a decision that has five allowed outputs.

The product question is whether Jev improves those decisions enough to justify a
new external dependency without damaging source recall, privacy, keyless use, or
provider-independent operation.

## Hypotheses

1. Jev can distinguish usable evidence, contradiction, irrelevant material,
   hostile instructions, and insufficient context on representative passages.
2. Its probabilities can support a conservative uncertainty band calibrated on
   GroktoCrawl cases rather than copied from provider examples.
3. A direct, bounded client can fail open without affecting incumbent API, CLI,
   MCP, synthesis, or keyless behavior.
4. Passage triage will either show enough value to justify a private frozen
   comparison or terminate the wider Jev candidate list early.

## Boundaries

- The adapter is observational. It does not filter, reorder, publish, verify, or
  rewrite evidence.
- No public route, request field, CLI flag, or stable environment setting is added.
- No private, authenticated, personal, or sensitive content is sent during this
  spike. The initial corpus is public and synthetic.
- SlopSearX engines, ranking, adapters, and routing remain outside this work.
- Jev does not replace deterministic barriers or the generative synthesis model.
- Provider-specific performance results remain private unless publication is
  separately authorized under the applicable TypeSafe agreement.

## Current evidence

The code supplies a strict client contract, frozen questions, content-free
receipts, deterministic provider fixtures, absent-key behavior, and an exposed
synthetic calibration corpus. An owner-authorized, bounded live technical smoke
exercised that corpus. A subsequent private frozen comparison stopped at its
predeclared operational-failure gate before validation; no product-value result
or calibrated threshold exists. Detailed provider results remain private.
The [outcome](outcome.md) records the no-ship decision and its limits.

## Provider-fact snapshot

Checked against TypeSafe's public documentation on 2026-09-20:

- the HTTP contract is `POST https://api.typesafe.ai/v1/systemone` with bearer
  authentication and top-level `state`, `model`, and `questions` fields;
- Jev 1.13 is identified as `jev-1.13.0`; the adapter pins that version rather
  than the moving `jev-latest` alias;
- the documented request budget is 64k tokens overall and 32k tokens for state
  plus the longest question; the published limits are 250,000 tokens/second and
  1,200 requests/minute, with a warning that limits may change;
- published pricing is $0.042 per million input tokens, with output tokens free;
- `429` and `529` responses are documented as retryable with backoff. This
  shadow adapter deliberately does not retry, keeping latency and spend bounded;
- TypeSafe says customer inputs are not used to train or fine-tune models. Its
  public agreement nevertheless permits service processing and unrestricted
  telemetry processing, and ordinary privacy terms retain personal data as long
  as reasonably necessary. Enterprise ZDR is mentioned but is not established
  for this spike.

These are vendor-published facts, not observed GroktoCrawl measurements or legal
approval. The first live run remains limited to public, low-risk text and still
requires the account-specific agreement, retention, publication, and spend review.

Sources: [API reference](https://docs.typesafe.ai/api),
[models](https://docs.typesafe.ai/models),
[privacy policy](https://typesafe.ai/legal/privacy-policy), and
[master customer agreement](https://typesafe.ai/legal/mca).

## Disposition

Reject/defer Jev passage triage for GroktoCrawl X under #360. This is a
readiness decision, not a claim that Jev is intrinsically inaccurate. No ADR
selecting Jev, production feature, default activation, or expansion to other
candidate uses follows from this spike.
