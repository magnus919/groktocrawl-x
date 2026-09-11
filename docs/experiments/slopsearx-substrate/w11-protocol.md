# W11 frozen-protocol candidate

Status: **draft; measurement prohibited until the freeze gate passes**

This protocol evaluates SlopSearX 0.5 as an optional research retrieval
substrate for GroktoCrawl. It follows the Academic/Comprehensive research track
and the agent-evaluation rule that task outcomes, trajectory behavior, and
operational claims need separate evidence.

## 1. Freeze gate

Before any scored run, commit one immutable `w11-freeze.json` containing:

- the accepted W10 result and selected control-policy identifier;
- GroktoCrawl source revision and container image digest;
- SlopSearX source revision, package version, image digest, MCP capability
  response, enabled grants, operator ceilings, engine configuration, and
  container configuration hash;
- model route name, prompt digests, case-file digests, runner and validator
  digests, random seed, work-order digest, and analysis-plan digest;
- exact cumulative limits for model calls, distinct queries, search attempts,
  engine attempts, admitted results, elapsed time, and stored bytes;
- system clock, run date, and explicit handling of time-sensitive cases.

The first release candidate is SlopSearX `0.5.0` at source revision
`edeba9ef9311adf19ce3f1b6060257ef1b54c2f9`. The installed deployment is
discovery evidence only. W11 uses an isolated deployment with a separate
tenant, Valkey namespace, credentials, network, and output directory.

Any change to a frozen input invalidates affected measurements. Preserve the
old run with an exclusion reason; never overwrite it.

Each isolated arm is prepared with `scripts/prepare_w11_arm.py`. The tool writes
an exclusive private environment file and a secret-free manifest, rejects
missing provider credentials, unsafe port ranges, and use of one port for both
services, and sets every undeclared grant to false. The fixed arm matrix is:
control (no specialist grants), research,
staged search, receipts, staged-plus-receipts, saved searches plus events, and
dependency dossier plus its required research and security grants. Each arm
uses a distinct Compose project name and distinct host ports.

## 2. Capability and compatibility preflight

Before model-bearing work:

1. Record `slopsearx_list_capabilities` and service status with secrets
   removed.
2. Prove every disabled workflow and domain grant fails closed, and verify the
   separate targeted-sensitive-engine policy.
3. Enable only the grants needed for the active arm.
4. Run the repository's SearXNG-compatible `/`, `/search`, `/config`,
   `/health`, and `/healthz` contract checks against the isolated 0.5 instance.
5. Repeat the same HTTP checks after all experiments.
6. Confirm MCP snapshots are tenant isolated and expire according to the
   declared retention policy.

Ordinary HTTP compatibility is a hard gate. A regression cannot be averaged
against better research scores.

## 3. Experiment families

The features answer different questions and therefore are not collapsed into
one leaderboard.

### A. General research coordination

Use the 12 W10 challenge cases. Add the 24-case W10 anchor only if the challenge
comparison passes all integrity gates and produces a decision-relevant signal.

| Arm | Behavior |
|---|---|
| A0 — flat control | The W10-selected GroktoCrawl policy plans each query and calls ordinary HTTP search. |
| A1 — recorded continuation | GroktoCrawl declares the same gaps and proposed queries; SlopSearX executes them through `start_research` / `extend_research`, accounts for attempts, and preserves snapshots. GroktoCrawl alone declares completion. |

Both arms use identical model prompts, gap decisions, query limits, engine
scope, result limits, acquisition rules, and final assessment. A1 may change
transport and persistence, but it may not generate a query, decide that a gap
is closed, or stop research on SlopSearX's behalf.

The challenge work order is generated only from a completed W10 summary. For
each challenge type selected by W10, both W11 arms use the W10 `full` policy;
all other types use `fixed`. The generator rejects partial W10 results and
freezes the exact summary and case-file digests. It counterbalances A0/A1 order
within every case and repetition so transport order cannot be chosen after
outcomes are visible.

Run three repetitions per case and arm in a deterministic, seeded,
counterbalanced work order. Repetitions measure run variability; they are not
treated as independent cases in uncertainty estimates.

Primary outcome: paired case-level change in importance-weighted claim closure.

Co-primary guardrail: admitted-source precision must not be worse by more than
the non-inferiority margin copied from the frozen W10 analysis. The margin may
not be chosen after seeing W11 outcomes.

Secondary outcomes: useful-query yield, unnecessary-query count, eligible
source diversity, acquisition success, elapsed time, model calls, search
attempts, engine attempts, result admissions, stored bytes, and completeness of
the research trajectory.

### B. Clean-empty staged fallback

Use a separately versioned set of at least eight deterministic cases covering:

- a precise initial scope that returns useful results;
- a fully observed clean empty result where disjoint fallback is warranted;
- partial engine failure;
- timeout;
- invalid or overlapping fallback scope;
- exhausted adapter-call budget;
- retry of the latest failed stage;
- policy revocation between dispatch and read.

Compare direct two-scope dispatch with the staged contract under identical
engine-call and deadline ceilings. The staged arm passes only when it suppresses
fallback after a non-empty, partial, timed-out, or failed first stage and
dispatches fallback after a fully observed clean empty stage. Quality scores
are secondary because this family primarily tests dispatch correctness and
cost avoidance.

### C. Discovery-to-retrieval provenance and entity handling

Use deterministic fixtures plus live search cases with explicit CVE, package,
scholarly, repository, and advisory identifiers. For each eligible result used
by GroktoCrawl:

1. read the full MCP handoff record;
2. fetch the verbatim eligible URL through GroktoCrawl's own post-resolution
   SSRF controls;
3. record capture hash, redirect/canonical observations, passages, timestamps,
   and failure state;
4. submit an idempotent retrieval receipt;
5. export a manifest and verify discovery-to-capture linkage.

Test malformed, unsafe, expired, foreign-tenant, conflicting-idempotency, and
failed-retrieval paths. A receipt is an attributed observation, never a
verification verdict.

For entity projections, measure repeated acquisitions avoided and all
conflicting fields retained. Verify conservation of results and confirm that
groups never count as independent-source corroboration.

### D. Recovery and accounting

Inject interruption after reservation, after engine return, after snapshot
write, during downstream retrieval, and after receipt submission. For every
boundary, verify:

- all returned evidence remains readable;
- retries obey original ceilings and scope;
- interrupted reservations remain charged when the upstream call is
  ambiguous;
- idempotent replay does not create a second receipt or repeated engine call;
- late workers cannot overwrite a newer owner;
- the terminal reason describes execution state rather than research truth.

### E. Separate capability slices

Saved-search monitoring is evaluated with controlled source additions,
deletions, changes, no-change intervals, pause/resume, event acknowledgement,
and retention. Report detection accuracy, duplicate notifications, delay, and
missed changes. Do not include these results in Family A.

Dependency dossiers are evaluated on a versioned package/repository/advisory
set with explicit expected identifiers and relations. Report identity,
provenance, conflict preservation, completeness, and unsupported cases. Do not
generalize dossier results to open-domain research.

## 4. Scoring and uncertainty

- Compute all quality measures per case, then compare paired arm differences.
- Report medians, distributions, and bootstrap confidence intervals over cases.
- Keep challenge and anchor strata separate.
- Report all failures and missing assessments; never score missing output as a
  successful zero-cost result.
- Analyze outcome, trajectory, recovery, compatibility, and operator burden as
  separate dimensions. No scalar total score can conceal a hard-gate failure.
- Preserve three-run variability and order effects. Do not inflate the sample
  size by treating repeated runs as new research questions.
- Run the frozen primary analysis first. Mark every later sensitivity or
  exploratory diagnostic as such.

## 5. Human and model review

Blind arm identity and execution order. Adjudicate:

- a seeded 10% sample of admitted sources;
- every repeated source-grade disagreement;
- every high-importance claim-closure disagreement;
- every disagreement between interim and final gap state;
- every provenance break, entity conflict loss, or disputed recovery outcome.

Reviewers grade source relevance, source authority, passage support, claim
closure, and contradiction handling separately. Agreement is reported; model
grades do not become truth merely because they are schema-valid.

## 6. Decision rules

Recommend **adopt** only if Family A meets its frozen quality and precision
gates, every compatibility/provenance/recovery hard gate passes, and the
operational review finds a sustainable owner and rollback path.

Recommend **narrow adoption** when one or more bounded contracts provide clear
value but the complete research workflow does not. Each adopted contract must
name its use case and remain opt-in.

Recommend **reject** when the integration weakens research outcomes, crosses
the ownership boundary, fails a hard gate, or adds operational burden without
a decision-relevant benefit.

Recommend **further study** when uncertainty spans the frozen decision margin,
missingness is material, or an environment failure prevents a fair paired
comparison. Lack of statistical significance alone does not prove equivalence.

## 7. Final artifacts

The final pull request must include:

- research brief and chronological research log;
- freeze manifest, case manifests, work order, environment record, and
  exclusions;
- validator and analysis output;
- source-level records, receipts, research manifests, and claim ledger;
- compatibility and recovery reports;
- separate saved-search and dependency-dossier reports;
- competing-hypothesis analysis, pre-mortem, sensitivities, limitations, and
  operator assessment;
- an ADR with adopt, narrow-adopt, reject, or further-study status;
- roadmap and issue updates.

All public artifacts must omit credentials, private network addresses, and
unredacted model traces.
