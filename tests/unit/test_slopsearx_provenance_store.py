from __future__ import annotations

from dataclasses import replace

import pytest
from agent.experimental.slopsearx_provenance import (
    ProvenanceReference,
    reference_document,
)


def reference() -> ProvenanceReference:
    return ProvenanceReference(
        schema_version="groktocrawl.slopsearx_provenance_reference/1",
        contract="slopsearx.retrieval_handoff",
        contract_version=1,
        snapshot_id="snap-1",
        result_id="snap-1:0",
        receipt_id="receipt-1",
        manifest_sha256="a" * 64,
    )


def test_reference_document_is_canonical_and_bounded() -> None:
    raw, digest = reference_document(reference())
    assert raw.startswith(b'{"contract"')
    assert len(raw) < 8192
    assert len(digest) == 64


@pytest.mark.parametrize(
    ("field", "value"),
    [("observations_verified", True), ("publishable", True)],
)
def test_reference_cannot_grant_research_authority(field: str, value: bool) -> None:
    with pytest.raises(ValueError, match="cannot grant"):
        reference_document(replace(reference(), **{field: value}))
