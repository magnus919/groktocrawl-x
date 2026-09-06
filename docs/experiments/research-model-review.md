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
wires the adapter to `luna` by default, independently of the inherited production
`LLM_MODEL`. An explicit model argument can override it; failure never silently
falls back to `general` or `local`. The first live `luna` probe returned an HTTP
403 `user_model_access_denied`: the existing key permits only `general`,
`local` and `cron`. That key needs access to `luna`. Routing configuration is implemented, but successful Luna inference is not
yet established. Gateway diagnosis is separate from local transport validation.
