# Capture egress gateway component

This experimental component accepts HTTP CONNECT and absolute-form HTTP requests through the shared DNS/socket destination policy. It preserves TLS end to end, limits concurrency and transfer size, and bounds connection lifetime and cleanup. The separate loopback health handler reports process liveness only.

The opt-in `compose.capture-https.yml` overlay adds a separate inbound TLS
frontend for the experimental agent API. That frontend does not use this
gateway: this source-egress gateway remains unwired into the candidate source
clients, browser workers, and FlareSolverr until the full protected profile is
integrated. Neither the frontend nor this component qualifies protected
capture or authorizes a live study. Complete integration and negative
network/browser qualification remain tracked in issue #429 and proposed
ADR-0099.

Component validation uses local loopback fixtures and fake stalled writers; no external search or provider requests are required. The current gateway suite has 26 passing tests, including opaque tunnels, HTTP bodies, destination denial, request framing, byte/concurrency limits, cancellation and bounded cleanup. These tests prove their declared component scenarios, not production isolation.

Runtime CI also builds this Dockerfile and starts the image with `--network none`. Its probe checks the real entrypoint's loopback liveness endpoint and private-origin refusals. This image smoke test makes no origin requests and does not establish the future protected capture network's isolation.
