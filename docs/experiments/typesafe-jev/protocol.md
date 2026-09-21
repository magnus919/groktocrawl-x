# TypeSafe Jev shadow evidence-router protocol

Status: **bounded live technical smoke completed; matched comparison not frozen**

## Arms

- **Control:** the acquired source artifact continues through the incumbent path
  without a Jev decision. Existing retrieval order and deterministic barriers are
  unchanged.
- **Shadow treatment:** Jev reads the fixed query and passage and returns one route
  plus four independent probabilities. The result is recorded but cannot affect
  the control output.

Both arms use the same acquired text. Acquisition differences are not part of the
independent variable. This experiment does not change SlopSearX.

## Question contract

The frozen adapter asks one `Choice` question with these routes:

- `evidence`: useful support for the query;
- `conflict`: relevant evidence that challenges a premise or likely answer;
- `irrelevant`: no material help;
- `unsafe`: instructions aimed at manipulating an AI system;
- `uncertain`: insufficient or ambiguous state.

The same request asks four `Noul` questions: material relevance, usable evidence,
query contradiction, and prompt injection. Questions are independent and share the
same state. Code validates the complete route distribution and never repairs an
invalid response.

## Preflight corpus

`exposed-routing-corpus.json` contains twelve public synthetic cases across direct
support, independent corroboration, contradiction, topical near misses, unrelated
text, explicit injection, tool manipulation, ambiguous fragments, identity
ambiguity, derivative evidence, and relevant-but-empty text.

These cases are exposed calibration and transport fixtures. They cannot be called
held out and cannot establish product value. A private technical-smoke freeze
was recorded before using them with a credential; the provider-specific readout
remains outside the public repository. Before matched product-value measurement,
prepare a separate private manifest with immutable case hashes and reviewed
labels, including realistic GroktoCrawl passages that the provider has not
influenced.

## Required private freeze

Before the first live call, freeze:

- Jev versioned model ID, endpoint contract, questions, and code revision;
- case IDs, input hashes, strata, references, repetitions, and work order;
- independent reviewer and adjudication procedure;
- practical-effect threshold, maximum source-recall loss, latency/cost ceiling,
  missing-result treatment, and launch exclusion rules;
- authorized input data classes, retention location, spend ceiling, and permitted
  publication surface;
- a statement that prior SlopSearX observations are external motivation rather
  than a comparison arm or GroktoCrawl result.

## Measurements

Primary:

- macro and per-stratum route accuracy;
- false exclusion risk for required evidence and contradictions;
- unsafe-instruction detection and false positives;
- uncertainty on incomplete or ambiguous passages;
- supported material claims and citation closure in the unchanged control answer.

Operational:

- p50/p95 incremental latency;
- requests, input/output tokens, and cost per completed research request;
- fallback, overload, rate-limit, timeout, and invalid-response rates;
- model-version identity and sensitivity;
- exact equality of keyless and provider-failure user-visible behavior.

Report case distributions and all failures. A missing result is not a favorable
classification. Do not infer calibration from confidence alone; measure it against
the frozen references.

## Execution

The exposed fixture can be exercised without a key:

```bash
UV_CACHE_DIR=/tmp/uv-cache PYTHONPATH=agent-svc:. \
  uv run --no-sync python scripts/run_typesafe_shadow_spike.py \
  --output /tmp/typesafe-shadow-preflight.json
```

Every record should be `skipped/key_absent`, proving that the runner makes no
network call and retains no decision without explicit credentials. A live run uses
the server-side `TYPESAFE_API_KEY` and writes to a private path. Never commit the
live ledger before legal/publication review.

## Stop rules

Stop immediately if data governance is unresolved, the key or raw response can
enter logs/artifacts, the adapter influences user-visible output, the cost ceiling
is reached, more than 10% of a launch ends in terminal provider failure, or keyless
equivalence fails.

Complete the planned repetitions and then stop. Passage triage must clear the
pre-registered quality, recall, latency, cost, and failure gates before evaluating
reranking or citation checking. A negative result is retained.

## Architecture disposition

No new ADR is proposed at preflight. The code is a bounded experimental adapter,
not an architecture selection. A follow-on ADR is required only if measured
evidence supports adopting a named Jev role.
