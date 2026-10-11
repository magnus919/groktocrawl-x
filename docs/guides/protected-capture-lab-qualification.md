# Protected capture lab qualification

`compose.protected-capture-lab.yml` adds deterministic, internal-only origin
and sentinel fixtures to the candidate profile. It does not replace the
configured LLM service or its route. The overlay intentionally contains no
`candidate-llm` service and does not change `candidate-model-egress` or
`candidate_model_upstream`.

Use the same ordered Compose files, project name, env file, fixture hostname,
and image set for configuration validation, startup, probes, and retained
receipts. The profile declares its egress network as `172.31.252.0/24`, separate
from the private `172.31.253.0/24` and fixed `172.31.254.x` capture networks;
none should be left for Docker's automatic address pool. Check these ranges
against host routes and existing Docker networks before starting the project.
The origin subnet is
internal to this project; the `capture-origin.example.test` name is a fixture
name, not a real destination. The host sentinel binds only the candidate
capture bridge gateway (`172.31.254.1`) on its two probe ports; the overlay
publishes no sentinel ports.

```bash
compose=(docker compose \
  --project-name "$CAPTURE_LAB_PROJECT" \
  --env-file "$CANDIDATE_ENV_FILE" \
  -f compose.experimental-candidate.yml \
  -f compose.protected-capture-lab.yml \
  -f compose.capture-https.yml \
  --profile protected-flare \
  --profile protected-capture)

"${compose[@]}" config --quiet
```

The private env file supplies the candidate's already-authorized model URL,
model alias, and API key, plus PostgreSQL/API secrets and HTTPS certificate,
private-key, and bearer-file paths. The client-side CA file is supplied
separately to the HTTPS probe. Do not print or copy these private values into
public artifacts. The overlay exposes only the non-secret `LLM_MODEL` alias to the probe as
`CAPTURE_PROBE_MODEL_NAME`. `CAPTURE_FIXTURE_HOST` may be set in that private
env file; its default is `capture-origin.example.test`. Changing it changes
the measured Compose configuration and requires a new config/profile receipt.

After separately authorizing a lab run, start the complete protected profile
from the prepared image set:

```bash
"${compose[@]}" up --no-build --pull never --detach --wait \
  candidate-capture-https candidate-scraper candidate-scraper-ingress \
  candidate-flare-control candidate-flare-test-origin \
  candidate-private-sentinel candidate-capture-peer-sentinel \
  candidate-host-bridge-sentinel
```

Run the existing ingress, egress, and Flare probes against that same project.
Their fixture URL and model alias come from the overlay while CI continues to
use the existing `flare-origin.test` and `fixture-model` defaults.

```bash
"${compose[@]}" exec -T candidate-private-sentinel python - \
  < tests/integration/scraper_ingress_boundary_probe.py
"${compose[@]}" exec -T --user 10001:20000 candidate-scraper python - \
  < tests/integration/scraper_egress_boundary_probe.py
"${compose[@]}" exec -T --user 10001:20000 candidate-scraper python - \
  < tests/integration/protected_flare_api_probe.py
"${compose[@]}" exec -T --user 10002:20000 candidate-browser-controller python - \
  < tests/integration/browser_capture_boundary_probe.py
"${compose[@]}" exec -T candidate-browser-renderer python - \
  < tests/integration/browser_renderer_isolation_probe.py
"${compose[@]}" exec -T candidate-flare-renderer python - \
  < tests/integration/protected_flare_renderer_probe.py
```

The egress probe makes one bounded completion request through the configured
model broker to verify that the real configured model path is reachable. It
must be included in the lab's authorized call budget. The other listed probes
exercise ingress, source capture, browser, Flare, and sentinel behavior. The
CI composition still uses its separate fixture-model overlay and is not a
substitute for a lab run. A passing configuration or synthetic test does not
qualify a deployed lab profile.

After probes finish, inspect both sentinel files in the private project volume:
`events.jsonl` must remain empty and `positive-control.jsonl` must contain the
single deliberate positive-control event. Retain those contents with the
resolved configuration hash and exact image inventory; never clear sentinel
events to make a later run appear clean.
