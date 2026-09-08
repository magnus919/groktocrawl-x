# W1 baseline inputs — 2026-09-08

Status: **baseline inputs frozen for review; scored comparison remains unauthorized**.

This record fixes the inputs that are already supported by the isolated packet
and incumbent run. It does not fill unresolved execution fields with defaults.
The fork remains an experimental project separate from mainline GroktoCrawl.

## Frozen inputs

| Input | Frozen value |
|---|---|
| Research domain | Enterprise agentic engineering and software factories |
| Held-out corpus | 30 unique cases; six categories; six template families; six adverse/abstention cases |
| Corpus digest | `sha256:659200d31ea23b17dc497b658c6c44db277005ed91a74fb962b10c6cebbf27c3` |
| Access-log digest after named review | `sha256:41e0d1be2c6ae5a8e35a628c5cb0c8bc7ec7d4dfce875bf98634b9817957d155` |
| Packet status | Structurally validated and approved eligible after named isolation review |
| Inference route | Internal LiteLLM gateway, `local` model alias |
| External provider spend | USD 0 |
| Incumbent arm | A, pinned upstream commit `34b4975bc7baaf25510ed34029b957f95b59de70` |
| Baseline order | Incumbent answer run completed before candidate arms |
| Trial accounting | Failed, timed-out, empty, and malformed outcomes remain in denominators |
| Quality claim | None yet; the baseline run has no semantic labels |

The raw packet and approval record remain outside the repository. The sanitized
isolation decision is recorded in
[w1-heldout-approval-2026-09-08.md](w1-heldout-approval-2026-09-08.md).

## Incumbent observation

The private incumbent run attempted all 30 cases through the local route:

- 29 valid answers;
- one malformed JSON response;
- 5,944 prompt tokens and 2,444 completion tokens, 8,388 total reported tokens;
- answer latency p50 6,424 ms and p95 8,283 ms.

These values describe the observed baseline run. They are not acceptance bounds,
quality scores, or evidence that a candidate is better.

## Still required before execution authorization

The following fields remain deliberately unresolved and continue to block a scored
series in `research-preflight.json`:

1. semantic grading and adjudication protocol, including the provisional one-human
   limitation;
2. quality, latency, resource, and per-run budget bounds derived from the observed
   baseline and reviewed before candidate execution;
3. candidate B/C commits and policy/runtime versions;
4. hardware, cache, model settings, paired order, and stochastic seed;
5. question-level uncertainty calculation and stop mechanism; and
6. explicit comparison authorization.

The minimum design remains five stochastic trials per held-out question per arm and
30 paired repetitions per runtime workload. Those are protocol minima, not an
authorization to run them. No production adoption, Qdrant removal, or mainline
replacement decision follows from this record.
