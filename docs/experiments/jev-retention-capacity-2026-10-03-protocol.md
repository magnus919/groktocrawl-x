# Bounded acquisition capacity probe (2026-10-03)

**Status: preregistered proposal; no live requests authorized until coordinator review.**
This protocol addresses the operational gap identified by the 2026-10-03
Jev-retention report. It is descriptive acquisition evidence, not a filter,
quality, or production-adoption experiment. It does not change configuration,
deploy a service, or modify the runtime.

## Frozen input and scope

Use the 34 distinct URLs in the privately retained EXP-035 `q1` candidate pool.
Its custodian verifies the exact pool by SHA-256
`9c903f589ef1c247aa7364b1769013032c1fb53088ebd98bd837d6d05ea9004d`; the
URLs, titles, snippets, and full page text remain outside this repository. Do
not issue a replacement search. This pool is a fixed returned candidate set,
not proof of complete engine coverage. All 34 URLs are eligible for one
attempt per arm. Do not retry failed, blocked, empty, or timed-out sources.

Use the existing candidate deployment only after the coordinator confirms its
health, revision, and zero unrelated active jobs. No deployment, environment,
feature-flag, cache, or service-state configuration changes are in scope. Do
not run Jev. Direct scrape calls use no LLM. Optional agent lifecycle probes
use model alias `free`, `force_fresh=true`, and only the small URL prefix
specified below. Search is not part of this experiment: every agent job receives
a fixed URL list; any observed search request invalidates that job and is
recorded. Model calls are bounded to at most eight total (planning/synthesis
across no more than four agent jobs); provider-reported usage and billing
remain unknown unless returned in the response. A read-only `/model/info`
lookup declared `max_input_tokens=1,048,576` for alias `free`; this is a
provider declaration, not an empirically verified routing limit, and does not
waive the small-input bound below.

## Workloads and bounds

1. **Direct scrape concurrency:** submit the identical 34 URLs once at caller
   concurrency 1, 3, and 5; then repeat each of those three sweeps once. Keep
   URL order fixed, permit at most one request per origin at a time, use no
   retries, and cap each call at 70 seconds. This is at most 204 scrape calls.
   The second pass is called a repeat, not a warm-cache result unless the
   service exposes an observable cache-state field; no cache is cleared.
2. **Optional agent lifecycle probe:** after the first direct pass, inspect
   only per-URL Markdown character counts in the private ledger. Select the
   longest prefix in frozen pool order, from one through five URLs, whose
   combined Markdown is at most 4,000 characters. Run no agent job unless the
   coordinator verifies a documented context limit for alias `free` and confirms
   that this measured input plus fixed prompt overhead fits. If no such limit
   is available, skip this entire component; do not treat that skip as a
   capacity test. For the selected prefix only, submit one streaming
   `/v2/agent` request (`force_fresh=true`, `max_credits` equal to prefix size)
   to observe progress, two simultaneous non-streaming jobs with the same
   prefix and bounds to observe concurrent status, and one non-streaming job
   with the same prefix for cancellation after admission. Poll job status to
   terminal. This is at most 20 additional URL attempts and four jobs; the
   cancellation attempt may finish before DELETE and is recorded as such.
3. **Health and resource observations:** record sanitized health and aggregate
   CPU/memory snapshots before, during, and after. Record per-candidate
   completion/failure class, response source tier, warning/degraded outcome,
   Markdown character count, and elapsed time in a private ledger. Publish only
   counts and descriptive aggregates. Do not log API keys, job IDs, full
   responses, prompts, or page text.

Total URL-attempt ceiling is 224 (204 direct calls plus at most 20 optional
agent-job attempts), with at most two agent jobs active at once, 70 seconds per
scrape, and a 30-minute wall-clock limit. No answer-quality rubric is applied.
Report the returned candidate-pool completeness separately from engine coverage, distinguish scraper failures from missing results, and
keep per-source outcomes; do not treat failures as irrelevant sources.

## Stop conditions and interpretation

Do not start unless candidate health is `ok`, there are no unrelated active
jobs, and the coordinator-reviewed proxy can read aggregate health/resources
and create, observe, stream, and cancel only these tagged probe jobs. Stop new
admissions immediately if health fails twice, the runtime revision changes,
an unrelated job appears, an upstream rate-limit response occurs, or the
30-minute/224-attempt/eight-model-call/four-job bound is reached. Preserve the
failure class and stop reason. Do not retry to fill missing observations.

Report completion count, failure/refusal/degraded counts, source-tier mix,
per-sweep latency summaries, observed concurrency, job terminal states,
progress event counts, cancellation outcome, and health/resource deltas. A
repeated pass is not a cache-warm result without explicit cache evidence. The
probe can describe this one 34-URL pool on this candidate revision; it cannot
establish general capacity, guarantee all-result success, or demonstrate
answer uplift. If the proxy cannot observe or cancel jobs, or the context prerequisite is
unmet, mark those lifecycle items unavailable and do not simulate their success
with client-side mocks. Even when run, the small-prefix job slice is not a
34-source end-to-end agent scheduling test.
