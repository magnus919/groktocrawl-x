# W11 research log

## 2026-09-11 — capability discovery

Question: Does the newly installed SlopSearX release change the experimental
roadmap?

Sources inspected:

- SlopSearX 0.5.0 source at revision
  `edeba9ef9311adf19ce3f1b6060257ef1b54c2f9`.
- `docs/ADAPTIVE_RESEARCH.md`: caller-directed continuation, durable budgets,
  immutable attempts, explicit caller completion, and operational stop reasons.
- `docs/STAGED_SEARCH.md`: precise scope plus disjoint fallback after a fully
  observed clean empty result, with deadline and adapter-call ceilings.
- `docs/RETRIEVAL_HANDOFF.md`: machine-readable discovery identity, downstream
  retrieval ownership, receipt semantics, and the mandatory downstream DNS/SSRF
  boundary.
- `docs/ENTITY_GROUPING.md`: explicit-identifier projection, conservation,
  unresolved singletons, conflicts, and the prohibition on treating a group as
  corroboration.
- `docs/MCP_SERVER.md` and the MCP tool registry: opt-in grants and the
  available research, staged-search, entity, receipt, saved-search, and dossier
  tools.

Observed deployment facts:

- The HAL2000 service reports package 0.5.0 and the source revision above.
- An authenticated MCP discovery call exposed 35 tools, including adaptive
  research, staged search, entity reads, receipts/manifests, saved searches,
  artifact lineage, and dependency dossiers. Tool discovery is not proof of
  authorization: disabled tools remain discoverable and must fail closed when
  called.
- The service-status contract reported 51 configured engines, connected
  Valkey, immutable snapshots, one concurrent durable research worker, a
  60-second lease, a 600-second default job deadline, a 20-query operator
  ceiling, a 500-result job ceiling, and a 3,600-second snapshot lifetime.
- The shared deployment enables research and selected domain grants, but does
  not enable staged search, receipts, saved searches, saved-search events, or
  dependency dossiers. Its workflow-health report says the implementations are
  available even where policy denies their use.
- The W10 candidate routes to its own pinned SlopSearX 0.4 container. Its
  experiment is therefore not split across releases.

Decision:

- Preserve W10 as the flat-search baseline.
- Evaluate 0.5 in W11 through an isolated, explicitly granted MCP deployment.
- Separate general research coordination, staged dispatch, provenance/entity
  handling, recovery, saved-search monitoring, and dependency dossiers so one
  feature cannot mask another's failure.

Preflight implementation check:

- The first capture was excluded because its configuration fingerprint
  included the current worker ID, which changes across restarts and is not a
  configuration choice.
- The corrected capture retains stable execution settings and omits that
  identity. Its configuration digest is
  `de343af62cb56eb4f6b0f2bcf32467269c058cae453ea23f4624bba7444cc167`.
- All five declared disabled capability probes returned `tool_disabled` before
  dispatch. The retained packet is under
  `evidence/slopsearx-substrate/2026-09-11-shared-discovery/` and remains
  excluded from scored W11 evidence.

Exclusions and limitations:

- Feature documentation and contract tests establish intended behavior, not
  GroktoCrawl integration value.
- The shared HAL2000 deployment will not be used for scored runs because its
  grants and workload are not isolated.
- W11 effect margins and the final control policy remain unset until W10
  finishes. No scored W11 run is authorized by this draft.
