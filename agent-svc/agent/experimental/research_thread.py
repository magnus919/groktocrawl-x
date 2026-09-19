"""Bounded longitudinal research-thread records; never an authority for truth."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Literal, Self

from pydantic import Field, field_validator, model_validator

from .knowledge import Identity, Record, Text

THREAD_SCHEMA = "research-thread-experiment/1"


class ThreadExperimentSource(Record):
    snapshot_id: Identity
    subject_id: Identity
    lineage_id: Identity
    title: Text
    text: Text
    source_role: Literal["primary", "independent", "derivative", "unavailable"]


class ExpectedThreadOutcome(Record):
    change_events: tuple[Text, ...] = Field(max_length=20)
    current_truths: tuple[Text, ...] = Field(max_length=20)
    historical_truths: tuple[Text, ...] = Field(max_length=20)
    unresolved: tuple[Text, ...] = Field(max_length=20)
    prohibited_merges: tuple[Text, ...] = Field(max_length=20)


class ThreadExperimentCase(Record):
    case_id: Identity
    stratum: Literal[
        "changed",
        "terminology",
        "derivative",
        "contradiction",
        "historical",
        "resolved",
        "unavailable",
        "near_match",
        "no_change",
    ]
    question: Text
    initial_question: Text
    subjects: tuple[ThreadSubject, ...] = Field(min_length=1, max_length=5)
    initial_sources: tuple[ThreadExperimentSource, ...] = Field(min_length=1, max_length=10)
    followup_sources: tuple[ThreadExperimentSource, ...] = Field(min_length=1, max_length=10)
    expected: ExpectedThreadOutcome

    @model_validator(mode="after")
    def case_integrity(self) -> Self:
        subjects = {item.subject_id for item in self.subjects}
        sources = (*self.initial_sources, *self.followup_sources)
        snapshot_ids = [item.snapshot_id for item in sources]
        if len(snapshot_ids) != len(set(snapshot_ids)):
            raise ValueError("case snapshot identities must be distinct")
        if {item.subject_id for item in sources} - subjects:
            raise ValueError("case source references an unknown subject")
        if self.stratum == "near_match" and len(subjects) < 2:
            raise ValueError("near-match case requires distinct subjects")
        return self


class ThreadExperimentCorpus(Record):
    schema_version: Literal["research-thread-corpus/1"]
    cases: tuple[ThreadExperimentCase, ...] = Field(min_length=9, max_length=20)

    @model_validator(mode="after")
    def complete_strata(self) -> Self:
        expected = {
            "changed",
            "terminology",
            "derivative",
            "contradiction",
            "historical",
            "resolved",
            "unavailable",
            "near_match",
            "no_change",
        }
        if {case.stratum for case in self.cases} != expected:
            raise ValueError("corpus must contain every longitudinal stratum")
        if len({case.case_id for case in self.cases}) != len(self.cases):
            raise ValueError("case identities must be distinct")
        return self


def load_thread_experiment_corpus(path: Path) -> ThreadExperimentCorpus:
    return ThreadExperimentCorpus.model_validate(json.loads(path.read_bytes()))


class ThreadSubject(Record):
    subject_id: Identity
    label: Text
    identifiers: tuple[Text, ...] = Field(min_length=1, max_length=20)

    @model_validator(mode="after")
    def unique_identifiers(self) -> Self:
        if len(set(self.identifiers)) != len(self.identifiers):
            raise ValueError("subject identifiers must be distinct")
        return self


class ThreadRoot(Record):
    root_id: Identity
    sequence: int = Field(strict=True, ge=0)
    created_at: datetime
    subject_ids: tuple[Identity, ...] = Field(min_length=1, max_length=20)
    snapshot_ids: tuple[Identity, ...] = Field(max_length=100)
    claim_ids: tuple[Identity, ...] = Field(max_length=1000)

    @field_validator("created_at")
    @classmethod
    def timezone_qualified(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("root time must include an offset")
        return value


class SourceLineage(Record):
    source_link_id: Identity
    prior_snapshot_id: Identity
    current_snapshot_id: Identity
    relationship: Literal["unchanged", "updated", "derivative", "link_rotated"]
    rationale: Text

    @model_validator(mode="after")
    def distinct_versions(self) -> Self:
        if self.prior_snapshot_id == self.current_snapshot_id:
            raise ValueError("source lineage requires distinct snapshot identities")
        return self


class ClaimLineage(Record):
    claim_link_id: Identity
    prior_claim_id: Identity
    current_claim_id: Identity
    relationship: Literal[
        "unchanged", "corrected", "superseded", "historical", "resolved"
    ]
    rationale: Text

    @model_validator(mode="after")
    def distinct_versions(self) -> Self:
        if self.prior_claim_id == self.current_claim_id:
            raise ValueError("claim lineage requires distinct claim identities")
        return self


class RecheckObligation(Record):
    obligation_id: Identity
    question: Text
    status: Literal["open", "satisfied", "blocked"]
    opened_in_root_id: Identity
    resolved_in_root_id: Identity | None
    evidence_snapshot_ids: tuple[Identity, ...] = Field(max_length=100)

    @model_validator(mode="after")
    def resolution_matches_status(self) -> Self:
        resolved = self.resolved_in_root_id is not None
        if resolved != (self.status == "satisfied"):
            raise ValueError("only satisfied obligations identify a resolving root")
        if self.status == "satisfied" and not self.evidence_snapshot_ids:
            raise ValueError("satisfied obligation requires evidence")
        return self


class ResearchThread(Record):
    schema_version: Literal["research-thread-experiment/1"]
    scope_id: Identity
    thread_id: Identity
    subjects: tuple[ThreadSubject, ...] = Field(min_length=1, max_length=20)
    roots: tuple[ThreadRoot, ...] = Field(min_length=1, max_length=20)
    source_lineage: tuple[SourceLineage, ...] = Field(max_length=200)
    claim_lineage: tuple[ClaimLineage, ...] = Field(max_length=2000)
    recheck_obligations: tuple[RecheckObligation, ...] = Field(max_length=200)

    @model_validator(mode="after")
    def closed_and_append_only(self) -> Self:
        subject_ids = _unique(self.subjects, "subject_id", "subject")
        root_ids = _unique(self.roots, "root_id", "root")
        sequences = [root.sequence for root in self.roots]
        if sequences != list(range(len(self.roots))):
            raise ValueError("thread roots must form an ordered append-only sequence")
        times = [root.created_at for root in self.roots]
        if times != sorted(times):
            raise ValueError("thread roots must not move backward in time")
        snapshot_ids: set[str] = set()
        claim_ids: set[str] = set()
        for root in self.roots:
            if not set(root.subject_ids) <= subject_ids:
                raise ValueError("root references an unknown subject")
            if len(set(root.snapshot_ids)) != len(root.snapshot_ids):
                raise ValueError("root snapshot identities must be distinct")
            if len(set(root.claim_ids)) != len(root.claim_ids):
                raise ValueError("root claim identities must be distinct")
            if snapshot_ids & set(root.snapshot_ids) or claim_ids & set(root.claim_ids):
                raise ValueError("new roots must not reassign snapshot or claim identities")
            snapshot_ids.update(root.snapshot_ids)
            claim_ids.update(root.claim_ids)
        _unique(self.source_lineage, "source_link_id", "source lineage")
        _unique(self.claim_lineage, "claim_link_id", "claim lineage")
        _unique(self.recheck_obligations, "obligation_id", "recheck obligation")
        for source_link in self.source_lineage:
            if {
                source_link.prior_snapshot_id,
                source_link.current_snapshot_id,
            } - snapshot_ids:
                raise ValueError("source lineage references an unknown snapshot")
            _require_forward_reference(
                self.roots,
                source_link.prior_snapshot_id,
                source_link.current_snapshot_id,
                "snapshot_ids",
            )
        for claim_link in self.claim_lineage:
            if {claim_link.prior_claim_id, claim_link.current_claim_id} - claim_ids:
                raise ValueError("claim lineage references an unknown claim")
            _require_forward_reference(
                self.roots,
                claim_link.prior_claim_id,
                claim_link.current_claim_id,
                "claim_ids",
            )
        for obligation in self.recheck_obligations:
            if obligation.opened_in_root_id not in root_ids:
                raise ValueError("recheck obligation references an unknown opening root")
            if obligation.resolved_in_root_id not in root_ids | {None}:
                raise ValueError("recheck obligation references an unknown resolving root")
            if set(obligation.evidence_snapshot_ids) - snapshot_ids:
                raise ValueError("recheck obligation references unknown evidence")
            if obligation.resolved_in_root_id is not None:
                opened = next(
                    root.sequence
                    for root in self.roots
                    if root.root_id == obligation.opened_in_root_id
                )
                resolved = next(
                    root.sequence
                    for root in self.roots
                    if root.root_id == obligation.resolved_in_root_id
                )
                if resolved < opened:
                    raise ValueError("recheck obligation cannot resolve before it opens")
        return self


def _unique(records: tuple[Record, ...], field: str, label: str) -> set[str]:
    values = [getattr(record, field) for record in records]
    if len(values) != len(set(values)):
        raise ValueError(f"{label} identities must be distinct")
    return set(values)


def _require_forward_reference(
    roots: tuple[ThreadRoot, ...], prior: str, current: str, field: str
) -> None:
    locations = {
        identity: root.sequence
        for root in roots
        for identity in getattr(root, field)
    }
    if locations[current] <= locations[prior]:
        raise ValueError("lineage must point from an earlier root to a later root")


def validate_research_thread(
    payload: object, *, scope_id: str, thread_id: str
) -> ResearchThread:
    """Validate an untrusted thread against caller-established ownership."""
    thread = ResearchThread.model_validate(payload)
    if (thread.scope_id, thread.thread_id) != (scope_id, thread_id):
        raise ValueError("thread differs from expected scope or identity")
    return thread
