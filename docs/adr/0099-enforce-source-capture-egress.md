# Enforce Source Capture Egress

- Status: proposed
- Date: 2026-10-09
- Scope: experimental fork only; no deployment or live-study admission
- Deciders: pending maintainer review
- Plan: [#429](https://github.com/magnus919/groktocrawl-x/issues/429)

## Context and Problem Statement

Initial URL validation does not bind a later connection to the validated DNS
answer. Redirects, adapter-owned clients, and browser requests can introduce new
destinations. Fresh research acquisition needs an enforceable destination boundary
without removing the browser and recovery capabilities that make capture useful.

## Decision Drivers

- Preserve all applicable adapters and the bounded recovery ladder.
- Reject forbidden destinations before connection, including DNS changes.
- Preserve existing deployment behavior until a protected profile is qualified.
- Keep fixed service-control destinations separate from source-selected traffic.
- Treat missing enforcement evidence as unavailable, not as successful protection.

## Considered Options

| Option | Benefit | Limitation |
|---|---|---|
| Initial URL checks | Small compatibility improvement | Cannot bind subsequent sockets or browser requests |
| Client proxy settings alone | Works with existing clients | Clients can bypass the proxy or fall back directly |
| Guarded gateway and isolated capture workers | One destination policy across tools | Requires transport and container qualification |
| HTTP-only study | Smaller validation surface | Removes useful capture tools and changes the experiment |

## Decision Outcome (Proposed)

Build a guarded gateway and an opt-in protected capture profile. Keep default
compatibility behavior until the profile has evidence for every applicable path.
Protected capture must fail before acquisition when a required component is not
qualified; it must not silently remove tools or fall back to direct connections.

The gateway resolves a destination once, validates every returned address, dials
a vetted numeric address, and verifies the socket peer. Each new destination,
including redirect targets and browser-generated requests, enters that policy.
Capture workers need an independently tested restriction on direct egress.
Proxy configuration alone is not that restriction. Browser rendering and
FlareSolverr remain available through the same boundary and recovery order.

Fixed internal service calls retain a separate trusted route. Source content
cannot select or inherit that route. Operator proxies in the protected profile
must preserve the validated destination binding; incompatible proxy behavior
fails preflight. Compatibility-mode proxy behavior remains unchanged.

If accepted, this would constrain the direct-fallback clause of ADR-0020 only
within the protected profile and extend ADR-0088 without changing its tool order.
The accepted records are not superseded by this proposal.

## Consequences and Limits

The profile introduces operational and testing work across HTTP clients, browser
workers, FlareSolverr, and network configuration. Unsupported deployment profiles
cannot claim protection. A passing policy unit test does not prove browser or
container enforcement. Implementation proceeds in reviewable increments, but
live-study admission requires the complete profile.

## Confirmation

Planned change-triggered unit tests cover mixed DNS answers, numeric dial binding,
peer mismatch, cancellation, timeouts, malformed authorities, and IPv4/IPv6 policy.
These confirm the connection primitive only.

The first implementation increment adds `common.capture_destination` and 45
synthetic tests, including the default resolver and numeric dialer paths. Those
tests pass, as do 67 existing URL tests, Ruff and the primitive's mypy check.
Independent review found no remaining P1/P2 defect in that primitive scope.
There is no client or gateway wiring yet; this evidence does not qualify capture.

Before enabling the profile, exact-image integration tests must exercise adapter,
metadata, redirect, inline-browser, browser-service, and FlareSolverr traffic.
Private sentinels must receive zero forbidden requests. Gateway outage, client
proxy bypass, and direct TCP/UDP attempts must fail closed while fixed service
calls and the full recovery ladder remain usable. Record source/image versions,
network profile, commands, and observed results. Missing evidence prevents admission.
Maintainer review owns any change to these requirements; no automatic exception
or replacement with a smaller tool set is permitted.

## Links

- [ADR-0020: Proxy support](0020-proxy-support-with-guardrails.md)
- [ADR-0088: Centralized bounded recovery](0088-centralize-bounded-barrier-recovery.md)
- [Initial destination guard PR](https://github.com/magnus919/groktocrawl-x/pull/428)
