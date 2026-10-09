# Capture egress gateway component

This experimental component accepts HTTP CONNECT and absolute-form HTTP requests through the shared DNS/socket destination policy. It preserves TLS end to end, limits concurrency and transfer size, and bounds connection lifetime and cleanup. The separate loopback health handler reports process liveness only.

It is not wired into Compose, source clients, browser workers, or FlareSolverr. It does not qualify the protected capture profile or authorize a live study. Complete integration and negative network/browser qualification remain tracked in issue #429 and proposed ADR-0099.

Component validation uses local loopback fixtures and fake stalled writers; no external search or provider requests are required. The current gateway suite has 26 passing tests, including opaque tunnels, HTTP bodies, destination denial, request framing, byte/concurrency limits, cancellation and bounded cleanup. These tests prove their declared component scenarios, not production isolation.
