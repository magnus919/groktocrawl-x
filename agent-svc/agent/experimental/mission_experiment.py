"""Deterministic W12.1 comparison mechanics, separate from model transport."""

from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .research_mission import MissionExperimentCase, render_control_brief

Arm = Literal["control", "treatment"]


def canonical_digest(value: object) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class WorkItem:
    trial_id: str
    case_id: str
    arm: Arm
    repetition: int
    position: int


def build_work_order(
    cases: tuple[MissionExperimentCase, ...], *, repetitions: int = 3, seed: int
) -> tuple[WorkItem, ...]:
    """Counterbalance arm position per case and shuffle cases per repetition."""

    if type(repetitions) is not int or repetitions != 3:
        raise ValueError("W12.1 requires exactly three repetitions")
    bases: dict[str, tuple[Arm, Arm]] = {}
    for case in cases:
        start: Arm = (
            "control"
            if int(hashlib.sha256(f"{seed}:{case.case_id}".encode()).hexdigest(), 16)
            % 2
            == 0
            else "treatment"
        )
        bases[case.case_id] = (
            ("control", "treatment") if start == "control" else ("treatment", "control")
        )
    result: list[WorkItem] = []
    for repetition in range(repetitions):
        case_order = list(cases)
        random.Random(seed + repetition).shuffle(case_order)
        for case in case_order:
            base = bases[case.case_id]
            order = base if repetition % 2 == 0 else (base[1], base[0])
            for position, arm in enumerate(order):
                result.append(
                    WorkItem(
                        trial_id=f"{case.case_id}-r{repetition + 1}-{arm}",
                        case_id=case.case_id,
                        arm=arm,
                        repetition=repetition + 1,
                        position=position + 1,
                    )
                )
    return tuple(result)


class ClaimResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    text: str = Field(strict=True, min_length=1, max_length=2_000)
    source_ids: tuple[str, ...] = Field(max_length=10)
    uncertainty: str = Field(strict=True, min_length=1, max_length=1_000)


class ObligationResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    status: Literal["supported", "contested", "unresolved"]
    source_ids: tuple[str, ...] = Field(max_length=10)
    rationale: str = Field(strict=True, min_length=1, max_length=2_000)


class DownstreamResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    answer: str = Field(strict=True, min_length=1, max_length=20_000)
    citations: tuple[str, ...] = Field(max_length=20)
    claims: tuple[ClaimResult, ...] = Field(min_length=1, max_length=30)
    obligation_results: dict[str, ObligationResult] | None

    @model_validator(mode="after")
    def citation_closure(self) -> DownstreamResult:
        cited = set(self.citations)
        linked = {source for claim in self.claims for source in claim.source_ids}
        if linked - cited:
            raise ValueError("claim sources must appear in the rendered citation set")
        return self


def build_downstream_prompt(
    case: MissionExperimentCase,
    *,
    sources: tuple[dict[str, str], ...],
    arm: Arm,
) -> dict[str, Any]:
    source_ids = {item["source_id"] for item in sources}
    if source_ids != set(case.source_ids):
        raise ValueError("trial source pack differs from the frozen case")
    common = {
        "task": (
            "Produce a decision-support answer using only the supplied source pack. "
            "Cite source_id values, preserve contradictions, and state unresolved limits."
        ),
        "sources": list(sources),
        "output_contract": {
            "answer": "final user-visible markdown",
            "citations": "all source_id values used by the rendered answer",
            "claims": "material claims with source links and uncertainty",
        },
    }
    if arm == "control":
        common["research_request"] = render_control_brief(case.reference_mission)
        common["obligation_results"] = None
    else:
        common["research_mission"] = case.reference_mission.model_dump(mode="json")
        common["output_contract"]["obligation_results"] = (
            "one status, source list, and rationale for every mission obligation"
        )
    return common


def validate_downstream_result(
    payload: object, *, case: MissionExperimentCase, arm: Arm
) -> DownstreamResult:
    result = DownstreamResult.model_validate(payload)
    allowed_sources = set(case.source_ids)
    observed_sources = set(result.citations)
    observed_sources.update(
        source for claim in result.claims for source in claim.source_ids
    )
    if observed_sources - allowed_sources:
        raise ValueError("result cites a source outside the frozen case")
    if arm == "control":
        if result.obligation_results is not None:
            raise ValueError("control result must not receive treatment obligations")
    else:
        expected = {item.obligation_id for item in case.reference_mission.obligations}
        if (
            result.obligation_results is None
            or set(result.obligation_results) != expected
        ):
            raise ValueError("treatment must account for every frozen obligation")
        linked = {
            source
            for item in result.obligation_results.values()
            for source in item.source_ids
        }
        if linked - allowed_sources:
            raise ValueError("obligation result cites a source outside the frozen case")
    return result


def sealed_grade_candidate(
    result: DownstreamResult, *, candidate_id: str
) -> dict[str, Any]:
    """Remove arm-only state and emit the identical review surface for both arms."""

    return {
        "candidate_id": candidate_id,
        "answer": result.answer,
        "citations": list(result.citations),
        "claims": [item.model_dump(mode="json") for item in result.claims],
    }


def work_order_record(items: tuple[WorkItem, ...], *, seed: int) -> dict[str, Any]:
    rows = [item.__dict__ for item in items]
    return {
        "schema_version": "research-mission-work-order/1",
        "seed": seed,
        "trials": rows,
        "trials_sha256": canonical_digest(rows),
    }
