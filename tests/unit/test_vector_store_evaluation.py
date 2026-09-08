"""Deterministic checks for the isolated vector-store evaluation harness."""

import importlib.util
import sys
from pathlib import Path

SCRIPT = Path(__file__).parents[2] / "scripts" / "run_vector_store_evaluation.py"
SPEC = importlib.util.spec_from_file_location("vector_eval", SCRIPT)
assert SPEC and SPEC.loader
vector_eval = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = vector_eval
SPEC.loader.exec_module(vector_eval)


def test_manifest_is_pinned_and_deterministic():
    first = vector_eval._manifest()
    second = vector_eval._manifest()

    assert first == second
    assert first["schema_version"] == "vector-store-evaluation/1"
    assert first["dimension"] == 3
    assert first["record_count"] == 6
    assert len(first["corpus_sha256"]) == 64


def test_qdrant_point_ids_are_supported_and_stable():
    first = vector_eval._qdrant_point_id("doc-001")
    second = vector_eval._qdrant_point_id("doc-002")

    assert first == vector_eval._qdrant_point_id("doc-001")
    assert first != second
    assert 0 <= first < 2**64


def test_reference_search_filters_scope_and_ranks_cosine():
    results = vector_eval.reference_search(list(vector_eval.CORPUS), vector_eval.QUERIES[0])

    assert [item["id"] for item in results] == ["doc-001", "doc-002", "doc-003"]
    assert all(item["id"] not in {"doc-004", "doc-005", "doc-006"} for item in results)


def test_reference_and_in_memory_store_enforce_soft_delete():
    store = vector_eval.InMemoryReference()
    store.upsert(list(vector_eval.CORPUS))
    store.delete("doc-001")

    result_ids = [item["id"] for item in store.search(vector_eval.QUERIES[0])]
    assert result_ids == ["doc-002", "doc-003"]


def test_gates_fail_closed_for_missing_or_wrong_results():
    evidence = {
        "ok": True,
        "errors": [],
        "searches": [
            {"query_id": vector_eval.QUERIES[0].query_id, "results": [{"id": "doc-004"}]}
        ],
        "post_delete": {"results": [{"id": "doc-001"}]},
    }

    gates = vector_eval._check_gates(evidence, list(vector_eval.CORPUS))

    assert gates["provider_ok"] is True
    assert gates["top_k_alpha-x"] is False
    assert gates["scope_alpha-x"] is False
    assert gates["deleted_doc_absent"] is False


def test_ranking_gate_allows_order_changes_inside_score_ties():
    expected = [
        {"id": "doc-004", "score": 1.0},
        {"id": "doc-005", "score": 0.0},
        {"id": "doc-006", "score": 0.0},
    ]
    actual = [
        {"id": "doc-004", "score": 1.0},
        {"id": "doc-006", "score": 0.0},
        {"id": "doc-005", "score": 0.0},
    ]

    assert vector_eval._ranking_matches(expected, actual)
    assert not vector_eval._ranking_matches(expected, [actual[1], actual[0], actual[2]])
