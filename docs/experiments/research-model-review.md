# Real-model research pilot

The full replacement roadmap is authorized under [issue #103](https://github.com/magnus919/groktocrawl-x/issues/103).
This slice connects a question to source acquisition, unverified knowledge
construction, executed model checks, three reports and a whole-report model audit.
It is an experimental developer runner. Public API/CLI/MCP delivery, retained
model publication, targeted follow-up and comparative evaluation remain unfinished.

## Run the pilot

Configure `SEARXNG_URL`, `SCRAPER_URL`, `LLM_BASE_URL` and `LLM_API_KEY` in the
process environment for reachable services. Credentials must never be committed.
The runner requests the owner-selected LiteLLM alias `local`:

```sh
PYTHONPATH=.:agent-svc .venv/bin/python scripts/run-research-pilot.py \
  'What evidence supports enterprise agentic software-factory productivity claims?' \
  /tmp/my-new-real-research
```

The directory must be new. The runner performs one search, acquires at most three
sources using lightweight scraping, and fails on acquisition barriers, warnings or
empty content. The query deadline is 180 seconds; cancellation is cooperative.
There are no automatic retries or alternate-model fallbacks. The model-call ceiling
is 64, with separate request/response byte and output-token-request limits. Actual
provider usage is observed rather than assumed to equal the requested ceiling.

After successful checks, it writes `summary.md`, `analysis.md`, `dossier.md`,
`knowledge.json` and `manifest.json`. The manifest is written last. `usage.json`
records dispatched model calls, reported model/token metadata, raw response digests
and failed/uncertain calls. Missing usage stays unknown, not zero. On failure there
is no successful manifest; previously dispatched work is not silently retried.
These files are not a retained PostgreSQL publication or a quality-comparison result.

## Model work and server-owned identity

`construct_research()` accepts captured sources from trusted acquisition callbacks.
The internal `research-construction/4` draft asks the model for up to six specific
source-statement claims, source-line selections, support/contradiction selections,
answer status and conflict descriptions. References are one-based positions in
bounded arrays. The model does not create scope, research, revision, evidence, claim,
question or graph-edge identifiers. The server assigns those and builds the existing
consolidated knowledge records.

The server extracts exact source lines and computes character offsets and hashes.
Repeated text is unambiguous because its line range identifies the occurrence.
Out-of-range, repeated or foreign references fail validation. Publication/effective
source dates remain unknown; capturing a document cannot establish current truth.
The initial policy supports statements about captured documents with historical
scope. Current-freshness checks cannot pass from unknown dates. Construction returns
unverified knowledge, never model-authored verification or human approval.

`ModelReviewAdapter` validates exact source bytes before each knowledge review and
sends the complete check context and source text. It accepts a strict decision bound
to the exact input digest. Structural, conflict/coverage, assessment, support and
freshness checks execute through the existing ledgers. A deterministic renderer
creates the three report layers from assessed claims. The render auditor receives
all three complete bodies and the pinned checked knowledge, including unmapped text.
Required negative or indeterminate judgments prevent successful publication eligibility.

`ConsolidatedJourney` accepts registered model/tool reviewers. The compatibility
entry point `ConsolidatedFixtureJourney` still rejects non-fixture reviewers, and
the fixture-only PostgreSQL writer is unchanged. Returned candidates are ephemeral;
closed execution owners cannot authorize a later retained commit.

## Transport and provenance

`ReviewTransport` uses a server-configured OpenAI-compatible endpoint and key with
an existing `httpx.AsyncClient`. It refuses redirects, bounds response bytes, and
rejects truncated, refused or tool-call completions. Provider error details are
suppressed from returned errors. Failed dispatches consume review call slots;
closed or cancelled owners reject late decisions.

Some compatible gateways return one complete Markdown `json` fence despite a JSON
request. The transport unwraps only that exact whole-response envelope and retains
the original content digest. It does not extract JSON from surrounding prose,
repair malformed JSON or change judgment fields. Strict canonical/schema admission
still runs afterwards. Prompt and generation configuration have explicit model
reviewer provenance. Model review is not independent human review or calibrated truth.

## Gateway evidence and current limits

Read-only inspection of `hal2000:docker-compose/groktocrawl` confirmed the existing
endpoint `https://gpuslut.brandyapple.com/v1` and configured authentication. A bounded
`local` completion succeeded with finish reason `stop`, reporting model `local`.
The mounted LiteLLM configuration on `gpuslut01` maps `local` to
`openai/Carnice-Qwen3.6-MoE-35B-A3B-APEX-MTP-I-Nano.gguf`. Record configuration and
returned identity separately: the response alias alone does not prove the backend.
Neither production deployment nor gateway configuration was modified.

Development probes found and retained failures for JSON code fences, paraphrased
quotes and invalid model-generated references. The transport envelope handling and
server-owned line/index mapping address those mechanical failure modes. These are
public-source development diagnostics, not a held-out or scored evaluation. Passing
structural tests does not establish research quality. Full live journey outcomes,
failed trials and later comparative evidence must be reported separately before
claiming improvement over the incumbent.

### Latest development result

The complete local suite passed 3,305 tests (seven skipped). The latest live
`local` probe used the consolidated-storage guide at commit
`b1e4fed414d3f5a8b46d43a74fced74c57ada33b` as one captured public source.
Construction and structural review completed, but conflict/coverage review returned
`conflicted`, outside the permitted `pass`/`fail`/`indeterminate` outcomes. The adapter
rejected the decision after three calls and 30.87 seconds; no reports or successful
manifest were produced. This is an unresolved model-contract reliability limitation,
not evidence of successful end-to-end research or an incumbent quality improvement.

Earlier development attempts also rejected null answer references and invalid
check outcomes. Required-answer and check-specific schema instructions preserve
strict admission, but prompting alone has not established reliable compliance.
The next live-readiness work must address this explicitly and retain failed trials;
it must not translate invalid labels into passing judgments or retry selectively
until a favorable result appears. No full search/scraper CLI run is claimed here.
