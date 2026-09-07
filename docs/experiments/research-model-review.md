# Real-model review integration

The full replacement roadmap is authorized under [issue #103](https://github.com/magnus919/groktocrawl-x/issues/103).
This first integration supplies provider-neutral knowledge-check and render-audit
callbacks. It is a component of the real-research path, not yet a query-driven
research endpoint or a research-quality result.

`ModelReviewAdapter` receives a trusted completion callback. Knowledge review
resolves and validates exact source bytes before dispatch, sends the full check
context and source text, and accepts only a strict decision bound to the input
digest. Render review receives all three complete report bodies and checked
knowledge through `RenderExecutionLedger`. Register its model reviewer and callbacks
with the existing execution ledgers; never convert a model reviewer into a fixture.
The fixture-only journey and storage gate remain unchanged in this slice.

The configured model, prompt and generation settings have explicit provenance.
Actual returned model identity and optional input/output token counts are retained
in the run-local adapter usage records. Missing usage stays unknown. These records
are not yet durable billing receipts. Limits cover calls, request/response bytes,
output-token requests and dispatch deadlines; a provider token request is not proof
of a financial spending ceiling. Failed or ambiguous calls consume their slots,
there are no automatic retries, and cancelled/closed owners reject late decisions.
Provider exception contents are suppressed from returned errors.

`ReviewTransport` uses an existing `httpx.AsyncClient` and server-configured
OpenAI-compatible endpoint/key. It refuses redirects, bounds response bytes and
rejects truncated, refused or tool-call completions. Credentials are not request
fields. The caller owns client lifecycle, authentication, shared admission and
provider spending policy. Tests use an HTTP mock and do not incur inference usage.

## Confirmed gateway route

On 2026-09-06, read-only inspection on `hal2000` found the existing deployment's
OpenAI-compatible endpoint at `https://gpuslut.brandyapple.com/v1` with configured
authentication. The gateway advertised `general`, `local`, `cron` and `luna`.
The initial requested alias was `general`. One bounded live completion
returned `READY` with model `deepseek/deepseek-v4-flash` and reported 91 prompt /
14 completion tokens. This establishes a working route at that time, not model
quality or a promise that alias routing cannot change. The production deployment
was not modified. Preserve the returned model identity in future comparisons.

Next: connect real construction, review and rendering to a query-driven journey;
retain real model provenance through publication, expose the API/CLI, and evaluate
against the incumbent using the same sources and model settings.

Magnus subsequently selected `luna` explicitly after a second `general` probe
still returned DeepSeek. `configured_model_review(client, base_url=..., api_key=...)`
initially wired the adapter to `luna` by default, independently of the inherited production
`LLM_MODEL`. An explicit model argument can override it; failure never silently
falls back to `general` or `local`. The first live `luna` probe returned an HTTP
403 `user_model_access_denied`: the existing key permits only `general`,
`local` and `cron`. That key needs access to `luna`. Routing configuration is implemented, but successful Luna inference is not
yet established. Gateway diagnosis is separate from local transport validation.

The latest owner instruction selected `local` for testing. Its bounded completion
succeeded with finish reason `stop`; the response reported model `local`, leaving
the underlying provider model unconfirmed. The configured adapter now defaults to
`local`, matching the working production alias. No automatic fallback is used.

## Query-driven construction in progress

`construct_research()` takes a question and up to eight already captured sources,
then makes one bounded model call through the same configured completion transport.
The model proposes claims, exact evidence quotes, relationships, the answer or
unresolved status, and conflicts. The server assigns scope/research/revision/source
identities, captured content hashes and quote locations. Missing or ambiguous quotes,
altered questions, invalid relationships and additional authority fields fail
admission. Publication/effective dates remain unknown unless separately established;
the model cannot supply them. Returned knowledge is explicitly unverified.

This is the construction component of R1. Search/acquisition dispatch, execution
budgets across stages, real verification/rendering/publication and API/CLI delivery
still need integration. Its local tests use scripted model responses and do not
establish real-model quality. The default completion model is the selected `local`
alias; there are no implicit retries or alternate-model fallbacks.

## First query-to-reports runner

The experimental `run_query()` now joins one search and up to three acquisitions
with construction, five check categories, deterministic three-layer presentation,
and a model audit of every complete output. Exact acquired source bytes are reused
for checks. Required negative or indeterminate judgments prevent successful output;
they are not retried until a favorable answer appears. This initial policy does not
yet deepen or reconcile disagreements. It supports captured-document historical
claims; unknown publication/effective dates cannot establish current freshness.

A separate `ConsolidatedJourney` accepts registered model/tool reviewers. The
existing `ConsolidatedFixtureJourney` keeps its fixture-only guard. Production routes
and the fixture-only PostgreSQL writer are unchanged. A successful model journey
returns an ephemeral candidate and files, not durable publication authority.

Configure `SEARXNG_URL`, `SCRAPER_URL`, `LLM_BASE_URL` and `LLM_API_KEY` in the
process environment for reachable services. The runner requests model alias `local`:

```sh
PYTHONPATH=.:agent-svc .venv/bin/python scripts/run-research-pilot.py \
  'What evidence supports enterprise agentic software-factory productivity claims?' \
  /tmp/my-new-real-research
```

The directory must be new. `summary.md`, `analysis.md`, `dossier.md`, canonical
knowledge and manifest are written only after successful checks. `usage.json`
records dispatched calls and reported token/model metadata, including uncertain
or failed calls; unknown usage is not zero cost. The bounded pilot uses lightweight
scraping and fails on acquisition warnings, barriers or empty content. It makes at
most 64 model calls, does not silently fall back to another model, and has a
180-second cooperative query deadline. This script is an experimental developer
entry point; public API/CLI/MCP integration, retained publication, targeted follow-up
and comparative evaluation remain roadmap work.
