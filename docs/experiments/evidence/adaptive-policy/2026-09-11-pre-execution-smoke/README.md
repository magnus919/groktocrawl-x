# W10 pre-execution smoke test

This packet preserves the failed smoke test that changed the acquisition
allocation before comparative execution. It is diagnostic evidence and is
excluded from W10 outcome calculations.

- Source revision: `416ad08`
- Host role: isolated experimental candidate
- Model route: `local` through the existing OpenAI-compatible gateway
- Case: `w10-01-unsupported-1`
- Policy reached: `gated`
- Result: read timeout at the frozen 90-second case limit
- Record timestamp: `2026-09-11T17:53:21Z`
- Record SHA-256: `e13a755266cdc017b04fc91f067624f7412374241bc74371f95a742fd0140e96`

Candidate API logs showed that search and page acquisition completed. The
single assessment request then exhausted the remaining case budget because it
contained as many as 24 acquired excerpts. The protocol now uses a declared
eight-page acquisition allocation while retaining metadata and exclusion
reasons for every returned result.
