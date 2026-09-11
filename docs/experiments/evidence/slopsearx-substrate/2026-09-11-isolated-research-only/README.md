# W11 isolated research-only preflight

This packet records the first successful startup of an isolated SlopSearX 0.5
MCP arm for W11. It is deployment and permission-boundary evidence, not scored
research-quality evidence.

The instance used its own Compose project, network, Valkey volume, bearer
credential, and host port. Only the research grant was enabled. Staged search,
retrieval receipts, saved searches, saved-search events, and dependency
dossiers were explicitly disabled and each denial was probed before dispatch.
The production GroktoCrawl deployment was not changed.

The retained preflight contains no credential, endpoint, private address, or
ephemeral worker identity. Its stable configuration digest is
`093ca7c87997db2ae5ec64aa8b816d012ee6ff2f19c7310841b64e3da4c752a6`.

The first startup attempt failed closed before any search because the Compose
wrapper incorrectly interpolated its container-side token reference. That
deployment defect was corrected and regression-tested before this packet was
captured.
