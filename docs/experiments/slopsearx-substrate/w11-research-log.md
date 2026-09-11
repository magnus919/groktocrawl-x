# W11 research log

## 2026-09-11 — installed 0.5 baseline and reference contracts

The HAL2000 GroktoCrawl deployment was rechecked after the operator reported
the new SlopSearX feature release. Both its HTTP and MCP containers identify as
SlopSearX 0.5.0 and resolve to the image digest already pinned by W11. The
ordinary deployment does not grant the new specialist workflows. This preserves
it as compatibility and discovery evidence; scored workflow experiments remain
isolated and enable only the grant required by each arm.

The 31-case contract manifest was then checked against 30 exact tests from the
pinned SlopSearX source. The local suite produced 111 passes and three deliberate
Valkey skips. Those three tests passed against the isolated W11 Valkey instance.
The generated secret-free summary binds both complete JUnit files by SHA-256 and
maps every case to its proof. Raw JUnit remains private because it contains
machine-local paths. An earlier collection attempt is excluded: six references
omitted their pytest class scopes. The manifest and validator were corrected
before the successful run; no outcome was inferred from the failed collection.

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

## 2026-09-11 — deployment contract refresh

A second authenticated preflight after the HAL2000 upgrade reproduced the
same 0.5.0 contract: all 35 expected tools were present, research was enabled,
the other five W11 specialist grants were denied before dispatch, and all five
workflow implementations reported healthy. Apart from the evidence label and
the distinction between the registry manifest digest and local image ID, the
stable preflight fields matched the retained discovery packet.

The experimental Compose contract now pins both the ordinary SlopSearX service
and its optional MCP companion to the observed 0.5.0 registry digest. It also
passes every 0.5 specialist grant as an independent empty-by-default setting.
This is required for isolated W11 arms: enabling staged search must not silently
enable receipts, saved searches, event publication, or dependency dossiers.
Deterministic Compose, MCP-client, preflight, and case-contract tests passed.
The local workstation has no Docker executable. A clean checkout on HAL2000
rendered the Compose model successfully and confirmed the pinned 0.5 registry
digest plus nine empty-by-default specialist grant variables. Live isolated
startup remains a separate pre-measurement gate.

The first isolated startup exposed a Compose interpolation defect in the MCP
wrapper: its shell test used a single dollar sign, so Compose substituted the
operator's unset `MCP_AUTH_TOKEN` before the container received the separately
mapped `SLOPSEARX_MCP_AUTH_TOKEN`. The container therefore failed closed and
restarted continuously. The wrapper now escapes the reference for container
evaluation, and its deterministic test rejects the pre-fix form. This failed
startup produced no search or scored evidence.

After correction, the research-only arm became healthy with its own Compose
network and Valkey volume. The authenticated preflight found all 35 expected
tools, exactly one enabled specialist grant (`research`), eight explicit
pre-dispatch denials, targeted-sensitive access disabled, durable leased
execution, and connected isolated Valkey.
The redacted packet is retained under
`evidence/slopsearx-substrate/2026-09-11-isolated-research-only/` with stable
configuration SHA-256
`9c78149ff6543a77aca6032ae252b0e64cdf96a4849a160da8df0a36214ad93a`.
It is deployment evidence only; no scored research task was run.

The isolated ordinary HTTP service then passed the before-run compatibility
gate across HTML root, JSON GET and form-POST search on both compatible paths,
configuration, health, readiness, and invalid pagination. The redacted
nine-probe packet retains no endpoint, query, or result content and has stable
configuration SHA-256
`e4995ad273449aac341088c3789d164f433cf1d4320265019282bc4342bc5a6b`.

A no-dispatch routing preview resolved the HTTP `general` category to seven
engines, then reproduced the same ordered set through explicit-engine routing.
W11 will freeze that list and provide it to both flat HTTP and recorded
continuation arms. This closes an important confound: an intent-profile routing
difference can no longer be mistaken for a persistence or transport effect.
The public report contains engine names and a query digest, but no endpoint,
credential, search result, or private network detail.

To remove repeated manual secret and grant editing, the harness now prepares
private arm environments from a fixed matrix. It creates files exclusively at
private permissions, never places credentials or ports in the public arm
manifest, rejects missing provider credentials and a within-arm port collision,
and explicitly disables every capability outside the selected slice. The
dossier slice encodes SlopSearX's actual composite requirement for dossier,
research, and security grants rather than assuming one switch is sufficient.

The preflight originally enforced the six new workflow grants but merely
carried the older jobs, science, security, and targeted-sensitive settings as
unexamined service metadata. That was insufficient for an exact arm boundary,
especially because the dossier arm requires security. The preflight now checks
all nine specialist grants, runs denial probes for every disabled grant, and
verifies the separate targeted-sensitive flag.
The original six-grant capture remains in the evidence directory under an
explicit incomplete-boundary filename and is excluded from later freeze input.

## 2026-09-11 — general-comparison harness

The W11 A0/A1 harness now refuses to construct a work order until W10 is
complete. It maps challenge types selected by W10 to the `full` control policy
and all other types to `fixed`, then counterbalances the flat-HTTP and recorded-
continuation arms within every case and repetition. Both arms use the same
frozen W10 query sequence and explicit engine list.

The retrieval runner is resumable and separates raw results from public
accounting. Private checkpoints use restrictive permissions. Public records
contain query, scope, and result-URL hashes rather than query or result text. A
retained private checkpoint can reconstruct a missing public record without
another search; a public record with missing private evidence fails closed.
SlopSearX research jobs use deterministic idempotency keys and cumulative
query, attempt, engine-attempt, and result limits.

Quality grading is a separate blind stage. It uses the corrected W10 keyed
assessment schema, the same acquisition limits and `fixed`/`full` admission
rules, one model assessment per trial, and an arm-independent shuffle seed.
Raw excerpts and the exact model response remain private. The public grade
retains normalized source judgments, gap closure, accounting, and response
hashes.

The primary quality gate is now frozen before outcomes: the lower bound of the
case-bootstrap 95% interval must remain above a two-point closure degradation
and a five-point precision degradation. Repetitions are averaged within cases,
not counted as independent evidence. Passing establishes non-inferiority only;
adoption still requires compatibility, provenance, recovery, and sustainable
operations. No scored W11 retrieval or quality run has begun.

## 2026-09-11 — production baseline alignment

The newly installed SlopSearX containers were compared with the isolated W11
candidate by immutable image identity. Both resolve to the same 0.5.0 registry
digest and exact source revision already named by this protocol. The six
capability families that motivated W11 are present in that source release.
This operational update therefore does not change a frozen input or require a
replacement candidate. Scored work continues only in isolated arms so normal
traffic and operator grants cannot affect the comparison.

The discovery-to-capture harness now exercises the first cross-service
provenance path. It reads a SlopSearX result handoff, lets GroktoCrawl perform
the page capture, submits the capture or failure as an attributed receipt,
replays the receipt to prove idempotency, and checks the exported manifest for
complete result linkage. Raw result records and captured content remain in a
private artifact; the public record retains only hashes, states, and gate
outcomes. The harness also requires SlopSearX to disclose that downstream
receipts are observations rather than verification judgments.

The isolated provenance arm passed its least-grant preflight with all 35 tools
present, only retrieval receipts enabled, and the other eight specialist
grants denied before dispatch. Its first Compose start inherited the normal
deployment's exported MCP port and collided before the MCP service started.
The arm was recreated using only its own private port setting; the failed start
is excluded and produced no search evidence.

The first live chain admitted three results. All three preserved discovery
identity through receipt creation, identical replay, retained receipt read,
and manifest export. GroktoCrawl captured and hashed two pages; one eligible
page returned an HTTP error and was recorded as a failed retrieval. The
provenance hard gate passed because the failure remained faithfully linked and
the manifest disclaimed verification. This result does not count the failed
page as successful acquisition and does not establish research quality.
