# Jev continuation and saved-search monitoring run

Status: **bounded feasibility screen completed; results are exploratory, not
quality-supported.** The first transport attempt failed and was preserved;
after explicit destination-specific authorization, the identical frozen cases
completed through the configured proxy.

## Frozen run

- Case-freeze commit: `0a967fa2bd782fd6b70bf6ee9dda3f20c75ae14d`
- Preregistered model: `jev-1.13.0`
- Frozen case packet SHA-256: `7d519f76c9a8f6318218a75490abc413b2390722192f9a01b61058eb11f842aa`
- Initial failed receipts SHA-256: `3af5c3500e6c48dc17b5de647146ee1e7262ad7cbdf122c21965c753729a9b8b`
- Authorized replay receipts SHA-256: `30cc03d532a2c16af30017f6115a49d187bd3950e4f8ad1e18cff99e29b1a3e2`
- Private receipts: `/private/tmp/gcx-jev-private-1003/receipts.json` and
  `/private/tmp/gcx-jev-private-1003/receipts-authorized-replay.json` (mode
  `0600`)
- Replay used the same packet and input digests; no labels, questions, cases,
  or packet contents changed. Calls were sequential, with no retries within
  either run.

The first runner execution recorded `provider_failure` on all 10 cases (4 #370,
6 #373), with no latency or usage. The runner collapsed the proxy error into
that generic status. A separate content-free readiness probe exposed
`proxy_transport` / SSH return code 255; the parent independently confirmed
healthy provider calls from its lane. The original receipts omitted raw errors,
so transport attribution rests on that probe and operator confirmation, not a
per-case raw error. Those attempts are preserved as transport failures, not
Jev semantic outcomes or a provider outage.

The authorized replay completed all 10 cases. #370 used 3,816 input and 184
output tokens; median provider latency was 221 ms (maximum 242 ms). #373 used
17,006 input and 272 output tokens; median was 195 ms (maximum 234 ms). No
response failed schema validation. Including the 10 original transport
failures, #370 used 8 attempts in its 25-call allocation and #373 used 12.

## What the run establishes

This is a small exposed-case feasibility screen. In #370 Jev chose `search` on
all four cases. That matched the best-effort reference for the contradiction
and unmet-gap validation cases, but disagreed on the met calibration case
(`no`) and unnamed-system/unanswerable case (`uncertain`). The evaluator-only
pool adds authoritative LangGraph interruption semantics for the contradiction
and a relevant cross-framework conformance study for the unmet gap; it cannot
answer the unnamed deployment's guarantee. These two alignments are not
independent gold and establish neither search quality nor calibration or
generalization. No fresh search query was issued.

In #373 Jev marked the synthetic boilerplate change `immaterial` and
version-specific change `material`, matching those constructed controls. It
also marked the synthetic fetch-failure control `material`; its reference is
`unevaluated`, because without the new page content no semantic-change
judgment is valid. All three real validation pairs were marked `material`,
matching best-effort assistant assessments of three related project-authored
documents. The labels are not independent gold and this sample is topic- and
author-context-biased. This screen does not justify automatic monitoring or
notification suppression. A deterministic fetch/change-identity gate must
remain authoritative; Jev cannot turn a fetch failure into a confirmed change.

The #370 packet has no fresh search or newly returned retrieval set. Its
evaluator-only pool replays existing search-snapshot evidence and known public
pages. Added evidence and decision-only cases are kept separate. The #373
validation material is not an independent or representative monitor corpus.

## Validation

The runner's four focused tests pass with `pytest --no-cov`. Ruff check and
format checks pass. The first privileged retry was rejected by automatic
review pending destination-specific approval. After the human explicitly
authorized the frozen public-document cases for TypeSafe, the unchanged packet
was replayed once. No application behavior, Hermes configuration, shared
roadmap, README, SlopSearX service, or mainline code changed.
