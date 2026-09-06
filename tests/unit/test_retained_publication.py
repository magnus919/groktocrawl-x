"""Publication admission binds caller context and exact retained structure."""

import json
from uuid import uuid4

import pytest
from agent.experimental.publication_store import admit_publication
from agent.experimental.revision_store import admit_revision

from tests.storage.publication_fixture import (
    CONTEXT,
    publication_payload,
    supported_revision,
)
from tests.storage.test_revision_store_db import payload


@pytest.fixture
def admitted_inputs():
    scope, root, revision, snapshot, publication = (uuid4() for _ in range(5))
    raw = supported_revision(
        payload(scope, root, revision, snapshot, b"Fixture source.")
    )
    structure = admit_revision(raw, scope, root, revision).structure
    return structure, publication, publication_payload(structure, publication)


def test_exact_outputs_and_canonical_representation(admitted_inputs):
    structure, publication, raw = admitted_inputs
    result = admit_publication(raw, structure, publication, CONTEXT)
    assert result.summary == result.analysis == structure.claims[0].text.encode()
    assert b'"verifications"' in result.dossier
    pretty = json.dumps(json.loads(raw), indent=2).encode()
    assert admit_publication(pretty, structure, publication, CONTEXT) == result


@pytest.mark.parametrize(
    "mutation",
    ["policy", "auditor", "revision", "set", "failed", "layer", "output", "extra"],
)
def test_invalid_context_or_audit_denied(admitted_inputs, mutation):
    structure, publication, raw = admitted_inputs
    context = CONTEXT
    data = json.loads(raw)
    if mutation == "policy":
        context = CONTEXT.model_copy(update={"policy_version": "other"})
    elif mutation == "auditor":
        context = CONTEXT.model_copy(
            update={"auditor": CONTEXT.auditor.model_copy(update={"version": "other"})}
        )
    elif mutation == "revision":
        data["revision_id"] = str(uuid4())
    elif mutation == "set":
        publication = uuid4()
    elif mutation == "failed":
        data["publication"]["audits"][0]["verdict"] = "fail"
    elif mutation == "layer":
        data["publication"]["audits"].pop()
    elif mutation == "output":
        data["publication"]["audits"][0]["checked_output_digest"] = "0" * 64
    else:
        data["extra"] = "unbound"
    with pytest.raises(ValueError):
        admit_publication(json.dumps(data).encode(), structure, publication, context)
