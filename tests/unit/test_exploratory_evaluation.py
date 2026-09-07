import json
from pathlib import Path

import pytest

from scripts.run_exploratory_evaluation import (
    answer_prompt,
    grade_prompt,
    load_cases,
    source_bundle,
    validate_answer,
    validate_grade,
)

CORPUS = Path("docs/experiments/enterprise-evaluation/corpus.json")


def _corpus() -> dict:
    return json.loads(CORPUS.read_text())


def test_load_cases_selects_exposed_candidates_without_expectations():
    cases = load_cases(CORPUS, limit=30)
    assert len(cases) == 30
    assert all(case["split"] == "calibration_candidate_exposed" for case in cases)
    assert all("expectation" not in json.dumps(case) for case in cases)


def test_prompts_keep_source_bundle_and_exclude_expectation_text():
    corpus = _corpus()
    case = next(case for case in corpus["cases"] if case["case_id"] == "delivery-03")
    sources = {source["source_id"]: source for source in corpus["sources"]}
    bundle = source_bundle(case, sources)
    assert "delivery-policy" in answer_prompt(case, bundle)
    assert "author_proposed_pending_review" not in answer_prompt(case, bundle)
    assert "delivery-03-r1" in grade_prompt(case, bundle, {"answer": "x", "citations": []})


def test_validate_answer_rejects_foreign_citation():
    with pytest.raises(ValueError, match="invalid citations"):
        validate_answer({"answer": "ok", "citations": ["foreign"]}, ["source"])


def test_validate_grade_requires_fixed_subquestion_denominator():
    case = next(case for case in _corpus()["cases"] if case["case_id"] == "delivery-03")
    with pytest.raises(ValueError, match="wrong subquestion denominator"):
        validate_grade(
            {
                "label": "ready_to_use",
                "rationale": "ok",
                "subquestions": {},
                "critical_finding": False,
            },
            case,
        )
