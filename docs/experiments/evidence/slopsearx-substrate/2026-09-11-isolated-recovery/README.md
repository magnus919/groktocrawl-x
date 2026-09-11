# W11 isolated recovery evidence

This packet closes the interruption boundaries that were missing from the
initial W11 contract summary. It uses the SlopSearX 0.5.0 runtime pinned by W11
and proof revision `ebfdd7d463515cd92b8309706aee1b6a095bb78e`.

## Results

- SlopSearX fault injection terminated a worker immediately after an engine
  response and immediately after snapshot persistence. Recovery retained the
  uncertain charge, marked the unfinished attempt interrupted, preserved a
  written snapshot, and completed without another engine call. These cases are
  included in the 33-case reference-contract summary.
- GroktoCrawl fixture injection interrupted an in-flight downstream capture.
  Resumption reused the search and handoff checkpoints. The ambiguous page
  request remained counted and the capture was tried once more.
- The live isolated arm terminated immediately after SlopSearX accepted a
  receipt. Resumption made no additional search, result-read, or capture call.
  The repeated receipt submission returned the original receipt identity, one
  receipt remained retained, the manifest stayed linked, and the hard gate
  passed.

The secret-free live outcome is in [after-receipt.json](after-receipt.json).
The private checkpoint retains the result, URL, captured material, and receipt
body outside the repository.

## Limits

The downstream-capture interruption is deterministic fixture evidence rather
than a live process kill. HTTP page retrieval can be ambiguous at interruption,
so the protocol permits one visible retry. It does not permit another search,
silent retry, or duplicate receipt. The live case proves the receipt boundary;
it does not turn a receipt into a verification judgment.
