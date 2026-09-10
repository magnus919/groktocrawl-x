# W1 replacement packet review — 2026-09-10

Status: **structurally valid; human isolation approval still required; comparison
not authorized**

Candidate B was frozen before this packet was created. Hermes then curated the
packet in a private directory outside the implementation workspace. The
implementation agent has not read or displayed its source text, questions, or
expected answers.

The repository records only the information needed to review the evaluation
boundary:

- 30 unique cases from 9 source records;
- 11 adverse or abstention cases;
- 8 topic categories and 30 distinct template families;
- no overlap detected with the exposed development corpus by the packet validator;
- corpus digest
  `sha256:99857f4484492e787adc62aab81189551f66ebcc3c9cd42f5bfdf7dcdc6dc796`;
- access-log digest
  `sha256:0f459327ffd3ced393ee653030ca5664ea985b228db10a2d947ddb9f9dc288dd`;
- validation-record digest
  `sha256:72aa09aa66df518151e5ef3b111fdbf78e39508c9e827390f18389bb58a51885`.

The first structural check found incorrect SHA-256 metadata on all nine source
records. An automated repair recomputed those fields from the already sealed UTF-8
text without printing any content. That access was added to the private access log,
the packet was resealed, and validation then passed with no structural errors.

This is enough to present the packet for Magnus's isolation review. It does not
make the packet held-out eligible by itself. Magnus still needs to approve the
curator and access history, after which the approval record can be added and the
separate scored-comparison gate can be considered.
