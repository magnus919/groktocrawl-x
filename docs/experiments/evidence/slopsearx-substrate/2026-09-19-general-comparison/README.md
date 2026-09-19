# W11 general-comparison execution packet

Status: **isolated research arm verified; scored measurement pending**

W10 selected fixed retrieval for every challenge type. The original private
trial directory was unavailable after the authorized pause, so this packet
derives the exact single-query control plans from the committed challenge cases
and binds them to the final W10 selection and complete public accounting.

- `w11-fixed-control-handoff.json` records the 36 derived case/repetition
  controls and the frozen eight-result search limit.
- `w11-work-order.json` counterbalances 72 flat HTTP and recorded-continuation
  trials across 12 cases and three repetitions.
- `preflight.json` records the live release identity, exact enabled and disabled
  grants, and fail-closed probes for every disabled specialist workflow.
- `http-compatibility-before.json` records a passing SearXNG-compatible HTTP
  surface before measurement.
- `scope-equivalence.json` proves that both arms start with the same frozen
  seven-engine search scope without dispatching a query.
- `w11-freeze.json` binds the 72-trial design, exact source and container
  identities, model route, resource ceilings, analysis plan, and every public
  input hash before the first scored query.

The freeze gate now distinguishes the two policy-only grants, `jobs` and
`science`, from grants written to the Compose arm manifest. Both still have to
appear in the live disabled set and return `tool_disabled` before measurement
can begin.

An initial execution attempt was rejected before scoring. All 36 recorded
continuation trials reached SlopSearX but the client treated the workflow's
successful plain-text completion acknowledgement as an error. Six of 36 flat HTTP trials
also encountered HTTP 429 responses. The 30 partial HTTP checkpoints are not a
valid comparison and will be discarded with the failures. The corrected runner
accepts the text acknowledgement, still rejects structured errors, and allows
at most five HTTP attempts with bounded `Retry-After` handling. The
freeze's request ceiling includes those attempts. Measurement restarts from an
empty checkpoint directory under a new frozen manifest.

The private handoff records contain the committed case queries and remain
outside the repository. This packet contains no result content, model response,
credential, or private network address. The recovery path fails closed if W10
selects any adaptive policy.
