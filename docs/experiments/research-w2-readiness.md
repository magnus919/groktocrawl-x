# W2 fixture readiness checkpoint

Scope: experimental GroktoCrawl X only; not a mainline replacement. Foundation
ADRs 0067–0070 and 0072 are accepted for bounded fixtures. Storage 0071 is accepted for bounded experimental exploration per issue #47;
runtime adoption 0073 and recovery 0074 remain proposed. This checkpoint accompanies issue
[#31](https://github.com/magnus919/groktocrawl-x/issues/31).

## Current conclusion

An executable local fixture journey now acquires text, constructs an immutable
structural revision, binds explicit assessment/verification/freshness records and
publishes an audited summary, analysis and dossier. The controller owns budgets,
cooperative deadlines, cancellation and terminal outcomes. A separate pure history
validator checks supplied revision chains. These are executable contract checks;
W2 is **not complete**, and the internal formats are not complete `knowledge-ir/1`.

The fixture author supplies claim annotations, assessment outcomes, semantic
verdicts and render wording. A passing test establishes that the implementation
honors those supplied expectations, not that the expectations are true, independent
or human-reviewed. Hosted integration proves regression compatibility, not research
quality. No provider has been added. Subsequent isolated PostgreSQL storage slices are
recorded below.

## Requirement-to-evidence matrix

| Accepted requirement | Implemented fixture evidence | Remaining limit or gate |
|---|---|---|
| ADR-0068: separate execution, knowledge and rendering | `pipeline.py` uses controller-owned acquire/construct/verify/render stages; bodies stay outside `ExecutionState`; `test_fixture_pipeline.py` | Finite local plan only. No independently evaluated research policy, adaptive search, bounded semantic repair loop or provider adapter. |
| ADR-0068: ownership, budgets, deadlines, cancellation | `execution.py`, `controller.py`; ledger/controller/pipeline tests exercise reserve-before-dispatch, stable receipts, late-result rejection and no failed/cancelled publication | Cooperative callbacks are trusted; blocking or cancellation-suppressing code cannot be forcibly stopped. No restart safety, leases or persistent ownership. |
| ADR-0069: exact evidence, identity, relationships | `knowledge.py`; Unicode spans, digests, scoped IDs, edge references and derivation DAG tests | Inline text fixtures only. Observation labels, semantic equivalence and source authenticity are not inferred or authenticated. Binary locators remain unspecified. |
| ADR-0069: freshness, source dependence and uncertainty | Source dates/provenance, lineage/origin, as-of context and historical/current scope; `test_source_freshness.py` | Dates and lineage are recorded assertions. No independent-source count or proof of current real-world truth. |
| ADR-0069: assessment distinct from verification | `FixtureAssessment` and explicit `AssessmentLink` mapping in `FixtureVerificationSet`; `test_fixture_assessments.py` | Fixture assessor shares the configured fixture identity contract. No real assessor authentication or independently evaluated semantic assessor. |
| ADR-0069: verification and publication eligibility | Input-bound support/freshness/conflict records plus exact three-layer audit binding; assessment alone cannot publish | Fixture verdicts can be wrong. No demonstrated entailment, caveat preservation or unbiased semantic audit beyond hand-authored cases. |
| ADR-0069: revision identity and append-only records | `revisions.py`; typed introductions, immutable IDs across removal/reintroduction, historical/current record separation | Bounded supplied linear history only; not authenticated, complete, persisted or portable. Declared novel/replacement semantics cannot be inferred. |
| ADR-0069: complete versioned IR | Separate structure, verification, publication and revision prototype formats implement substantial parts | Consolidated schema/examples and compatibility policy are not frozen as `knowledge-ir/1`. Claim-to-assessment links currently live in an explicit envelope mapping. Whole-IR interchange hashing depends on the D3 exploration contract; implementation and adoption gates remain. |
| ADR-0070: separate policy/runtime comparisons, frozen evidence, negative controls | Inherited deterministic regression baseline is pinned in `research-preflight.json`; fixture contract negative tests are executable | Independent semantic corpus/rubric/reviewers, arm definitions and comparison thresholds remain unresolved. Current fixture tests are not a completed A/B/C study. |
| ADR-0072: verified final output distinct from progress, stable identity and coverage | Internal controller final outcome, same-revision artifacts and complete/partial/insufficient coverage | No experimental HTTP/SSE, CLI/MCP, reconnect/replay or authorization implementation. Public delivery remains later W6 work. |

Implementation paths above are under `agent-svc/agent/experimental/`; test paths are
under `tests/unit/`. See the [implementation record](research-architecture.md) for
merged milestones and the issue/PR for the current CI evidence. Tests do not prove
requirements listed as remaining limits.

## Concrete next gate

Do not turn fixture test counts into an adoption decision or start an unfrozen
comparison. Prepare a reviewed evaluation design and a final schema gap disposition
before moving beyond the bounded fixture scope.

| Required input or decision | Proposed reviewable action | Decision owner / constraint |
|---|---|---|
| Target research workload and corpus | Choose a representative domain/question mix; freeze separate development and held-out source snapshots/questions, denominators and expected negative/abstention categories | Magnus selected enterprise agentic engineering/software factories. A synthetic calibration design is linked below; no sealed held-out corpus exists yet. |
| Independent semantic reviewers | Name primary and adjudicating reviewers and define blinded rubric/adjudication for support, scope, conflict, freshness and render additions | Magnus authorized Hermes as a separate AI reviewer and retains human calibration/adjudication. No human calibration labels are collected yet. |
| Measurement thresholds and resources | Record quality/latency/resource regression bounds with rationale, hardware, run budgets, seeds/order and uncertainty plan | Must be explicit before applicable comparisons. Existing protocol minima are not measured results or an authorized series. |
| Complete IR contract | Review each prototype field against ADR-0069, freeze the consolidated schema and reader/version policy, and resolve D3 interchange dependencies | Keep prototype names until this is complete. No implicit acceptance of proposed storage choices. |
| Provider-backed execution, if needed | Specify local/provider model and exact spending ceiling before connecting a real verifier or running it | Current external-provider budget is zero. No provider work is authorized here. |
| Runtime/storage/recovery decisions | Use accepted ADR-0071 exploration gates; ADR-0073/0074 remain proposed | Preserve the pgvector-versus-Qdrant consolidation evaluation and conditional PostgreSQL-native recovery option; PostgreSQL exploration is approved, not production/vector adoption. |

The authoritative unresolved fields remain in
[`research-preflight.json`](research-preflight.json). Null means unresolved; this
checkpoint does not fill them with permissive defaults, promote the regression
baseline or authorize comparisons. A useful next step is a concrete frozen-design
packet for the selected workload, not another unconnected implementation slice.

## Evaluation design follow-up

Magnus supplied the domain and reviewer direction after this checkpoint. See the
[enterprise evaluation design](enterprise-evaluation/README.md), tracked in issue
[#33](https://github.com/magnus919/groktocrawl-x/issues/33). The synthetic calibration
corpus and separate Hermes design review do not resolve the held-out, human
calibration, measured-baseline or comparative-execution gates.

## Canonical admission implementation

[Bounded canonical JSON admission](research-canonical-admission.md) implements
representation checks and JCS bytes for the approved storage exploration. It does
not freeze the complete IR schema or establish database lifecycle behavior.

The [isolated PostgreSQL harness](research-postgres-harness.md) introduces a real
database CI boundary for storage exploration. Its transport probes do not freeze
the research schema or complete the W3 lifecycle matrix.

The [retained-source staging adapter](research-source-storage.md) adds bounded
source transactions and receipts. Complete Knowledge IR remains unfinished; the subsequent fixture publication
extension is recorded below. Source staging alone does not complete W2 or W3.

[Retained structural revisions](research-retained-revisions.md) now pin scoped
source references and a parent chain transactionally. Complete Knowledge IR and
authenticated semantic verification remain separate unfinished gates.

The [retained fixture publication slice](research-retained-publications.md) adds
atomic audited outputs and pinned reference reopening on isolated schema 3. This
remains synthetic fixture evidence and does not complete W2/W3 or human calibration.

Explicit historical re-rendering now preserves the complete original research
envelope while creating a new audited fixture presentation on schema 4. This adds
reuse without retrieval; export/import and the remaining W3 gates are still open.

[Bounded artifact bundles](research-artifact-bundles.md) now support consistent
export and offline integrity validation with preserved original identities.
Recipient scope mapping and atomic import remain unimplemented.
