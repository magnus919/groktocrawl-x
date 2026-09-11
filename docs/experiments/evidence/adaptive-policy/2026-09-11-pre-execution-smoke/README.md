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

## Bounded-packet smoke

Revision `e84a23e` ran the same case after the acquisition correction:

| Policy | Result | Elapsed | Record SHA-256 | Manifest SHA-256 |
|---|---:|---:|---|---|
| fixed | completed | 41.792 s | `b1bdca6060912b4059ff866025f38126bea2f2954da3ebf7ed6c0d5eb836f502` | `30f3319669af97ac659f10072ed9d303d23e2e2734f5a7127fbcb4e6ac9eb34d` |
| full | completed | 78.897 s | `3a90ad5fb96cb01b7a14d9b6630cf6ce17ccb22b348048383aae61f3a32f96c5` | `a07f5af905974c4289dffda36e27a6d3008ad56e929d9f201edb2038d6110215` |

The full policy exposed a second pre-execution defect: the prompt did not define
`marginal_value`, and publisher identity was model-generated. The grader marked
useful claim evidence as non-marginal, causing the deterministic admission layer
to reject every source. Before comparative execution, publisher identity was
moved to URL-derived code and the grader schema was expanded to distinguish
claim value, authority gain, currency gain, and contradiction resolution. These
smoke outputs are excluded from outcome calculations; their complete records and
private acquisitions remain on the experiment host under `/tmp/w10-smoke-*`.
