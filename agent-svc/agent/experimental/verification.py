"""Input-bound fixture verdicts, not a semantic oracle or publication gate.

Only fixture expectations are accepted here. Human/model verifier authentication,
append-only storage and render audit are deliberately not simulated by this format.
"""

import json
from datetime import datetime
from typing import Literal, Self

from pydantic import Field, field_validator, model_validator

from .knowledge import Digest, Identity, KnowledgeStructure, Record, Text, text_digest


class FixtureVerifier(Record):
    kind: Literal["fixture_expectation"]
    identity: Identity
    version: Identity


class VerificationInput(Record):
    """Full structural context prevents a quote-only verdict from hiding context."""

    schema_version: Literal["fixture-verification-input/1"]
    structure: KnowledgeStructure
    subject_id: Identity
    check_type: Literal["semantic_support", "freshness", "conflict_coverage"]
    policy_version: Identity
    verifier: FixtureVerifier
    evidence_ids: tuple[Identity, ...] = Field(max_length=1000)

    @model_validator(mode="after")
    def local_references(self) -> Self:
        if self.subject_id not in {claim.claim_id for claim in self.structure.claims}:
            raise ValueError("verification subject must be a claim in this revision")
        available = {item.evidence_id for item in self.structure.evidence}
        if len(set(self.evidence_ids)) != len(self.evidence_ids):
            raise ValueError("verification evidence references must be unique")
        if not set(self.evidence_ids) <= available:
            raise ValueError("verification references unavailable evidence")
        return self

    def input_digest(self) -> str:
        """Prototype-specific JSON digest; NOT JCS or a whole-IR interchange hash."""
        checked = VerificationInput.model_validate(self)
        encoded = json.dumps(
            checked.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        return text_digest("fixture-verification-input/1\0" + encoded)


class FixtureVerification(Record):
    verification_id: Identity
    checked_input: VerificationInput
    checked_input_digest: Digest
    verdict: Literal["pass", "fail", "indeterminate"]
    checked_at: datetime
    reason: Text

    @field_validator("checked_at")
    @classmethod
    def utc_timestamp(cls, value: datetime) -> datetime:
        offset = value.utcoffset()
        if offset is None or offset.total_seconds() != 0:
            raise ValueError("checked_at must have an explicit UTC offset")
        return value

    @model_validator(mode="after")
    def exact_input(self) -> Self:
        if self.checked_input_digest != self.checked_input.input_digest():
            raise ValueError("verification input digest mismatch")
        return self


class FixtureVerificationSet(Record):
    """Binds recorded judgments to trusted expected context, never auto-approves."""

    schema_version: Literal["fixture-verifications/1"]
    structure: KnowledgeStructure
    policy_version: Identity
    verifier: FixtureVerifier
    records: tuple[FixtureVerification, ...] = Field(max_length=3000)

    @model_validator(mode="after")
    def bind_records(self) -> Self:
        identities = [record.verification_id for record in self.records]
        if len(set(identities)) != len(identities):
            raise ValueError("verification IDs must be unique")
        entity_ids = {
            *(item.snapshot_id for item in self.structure.snapshots),
            *(item.evidence_id for item in self.structure.evidence),
            *(item.claim_id for item in self.structure.claims),
            *(item.relationship_id for item in self.structure.relationships),
        }
        if entity_ids.intersection(identities):
            raise ValueError("verification IDs must not alias structural entities")
        for record in self.records:
            context = record.checked_input
            if context.structure != self.structure:
                raise ValueError("verification uses different structural context")
            if context.policy_version != self.policy_version:
                raise ValueError("verification uses different policy")
            if context.verifier != self.verifier:
                raise ValueError("verification uses different verifier")
        return self


def validate_fixture_verifications(
    payload: object,
    *,
    structure: KnowledgeStructure,
    policy_version: str,
    verifier: FixtureVerifier,
) -> FixtureVerificationSet:
    """Require caller-established input and verifier identity, not payload authority.

    The caller must first validate the structure against trusted scope with
    validate_structure. These fixture verdicts are deliberately forgeable test data,
    not authenticated human approvals or signed semantic verification evidence.
    """
    result = FixtureVerificationSet.model_validate(payload)
    if result.structure != KnowledgeStructure.model_validate(structure):
        raise ValueError("verification set differs from expected structure")
    if result.policy_version != policy_version or result.verifier != verifier:
        raise ValueError("verification set differs from expected policy/verifier")
    return result
