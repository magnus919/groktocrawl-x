# Protected FlareSolverr profile

This candidate-only profile preserves FlareSolverr's `/`, `/health`, and `/v1`
API, including request GET/POST, sessions, cookies, and the upstream Selenium
challenge logic. The candidate scraper points its existing FlareSolverr client
at the controller bridge only when the candidate Compose overlay is selected.
The ordinary Compose stack is unchanged.

## Frozen upstream input

The profile starts from FlareSolverr v3.5.2, the latest upstream release checked
for this implementation. The upstream release page identifies signed release
commit `93125d6`; the official GHCR image is pinned as
`ghcr.io/flaresolverr/flaresolverr:v3.5.2@sha256:c80ae007ce2ccdcd217a12426e4f039ef763ff90738c808d38810c3e59323767`.
The image contains Chromium and `/app/chromedriver`; upstream `utils.get_webdriver`
selects that bundled driver in Docker instead of downloading another driver.
The Docker build applies narrow source substitutions and fails if the expected
upstream source statements have changed. It adds no replacement browser or
challenge implementation.

Upstream accepts proxy configuration per request and session. The protected
patch overwrites that field at API ingress with the fixed candidate gateway,
validates request URLs to HTTP or HTTPS, and binds Waitress to a Unix socket.
The matching controller bridge on the candidate private network forwards only
the existing API paths to that socket. The Flare/Chromium container is not on
the controller network and has no TCP Flare API listener. The page fixture
attempts to fetch the API over loopback; the profile smoke test expects that
attempt to fail.

The browser receives the numeric gateway proxy, an explicit Chromium
`<-loopback>` proxy-bypass override, and disabled browser background update
traffic. The container firewall allows established traffic, loopback (needed
by the local Selenium/ChromeDriver control plane), and TCP to the gateway's
fixed internal address and port. It denies other direct IPv4 and IPv6 traffic.
Therefore this profile claims source egress is gateway-bound; it does not claim
that every loopback socket is unreachable from browser internals. The Flare API
itself is absent from those loopback TCP sockets and is reachable only through
the separate controller bridge and shared Unix socket.

## Local fixture qualification

The Runtime CI profile adds a synthetic origin on the public test address
`93.184.216.34` inside a Docker network marked `internal`; the gateway resolves
`flare-origin.test` to that address from its container hosts file. The network
has no route to external destinations. The origin exercises page load,
redirects, cookie return, screenshot capture, POST submission, and an in-page
attempt to reach the Flare API. The same test sends a caller-supplied proxy
pointing at the absent loopback API; successful fixture capture demonstrates
that the caller proxy did not replace the configured gateway. The control API
also verifies sessions create/list/destroy and rejects `file:` URLs.

To render the opt-in candidate profile, set the required candidate environment
values as described by `compose.experimental-candidate.yml`, then run:

```sh
docker compose --project-name candidate-flare \
  --env-file /path/to/candidate.env \
  -f compose.experimental-candidate.yml \
  --profile protected-flare \
  config --quiet

docker compose --project-name candidate-flare \
  --env-file /path/to/candidate.env \
  -f compose.experimental-candidate.yml \
  --profile protected-flare \
  up --build --detach --wait candidate-flare-control
```

The CI-only fixture overlay is intentionally omitted from these operator
commands. Do not publish or expose the Flare API or controller bridge outside
the candidate private network.

This is an opt-in integration candidate, not deployment or full capture-stack
qualification. The tests do not exercise real Cloudflare/DDoS-GUARD challenges,
external targets, every browser side channel, or production workloads. Keep
the protected profile unavailable if any component or negative boundary check
fails. The public FlareSolverr version and image identity can change upstream;
review and freeze a new source/image pair before updating the base pin.

## Primary sources

- [FlareSolverr v3.5.2 release](https://github.com/FlareSolverr/FlareSolverr/releases/tag/v3.5.2)
- [FlareSolverr v3.5.2 API server](https://github.com/FlareSolverr/FlareSolverr/blob/v3.5.2/src/flaresolverr.py)
- [FlareSolverr v3.5.2 challenge controller](https://github.com/FlareSolverr/FlareSolverr/blob/v3.5.2/src/flaresolverr_service.py)
- [FlareSolverr v3.5.2 Chrome and proxy setup](https://github.com/FlareSolverr/FlareSolverr/blob/v3.5.2/src/utils.py)
- [Official FlareSolverr GHCR package](https://github.com/FlareSolverr/FlareSolverr/pkgs/container/flaresolverr)
- [Chromium proxy settings](https://www.chromium.org/developers/design-documents/network-settings/)
