# W1 comparison launch record — 2026-09-10

Status: **qualification failure; no scored result**

The first authorized launch reached no model inference. All Arm A connection
attempts failed because the configured `gpuslut01` hostname did not expose the
LiteLLM port; the gateway is published on its LAN address. Arm B rejected its
private source aliases before transport because they were not valid HTTP URLs.

The private runner retained every attempted outcome. There are zero completed
answers and zero received model envelopes, so this launch is invalid for scoring
and supplies no evidence about either arm. The private launch manifest has digest
`sha256:16817fe7c9cec787f097210be067aee4bc2987237aaa39db90f57edf8151247e`.

The runner now checks the authenticated model listing before creating an output
directory and uses non-routable, contract-valid HTTPS identities for private
sources. A clean rerun requires an explicit amendment because the no-retry rule
was correctly conservative even though inference did not occur.
