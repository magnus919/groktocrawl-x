"""Deterministic checks for the bounded vector-store scale harness."""

import importlib.util
import sys
from pathlib import Path

SCRIPT = Path(__file__).parents[2] / "scripts" / "run_vector_store_scale_evaluation.py"
SPEC = importlib.util.spec_from_file_location("vector_scale_eval", SCRIPT)
assert SPEC and SPEC.loader
vector_scale_eval = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = vector_scale_eval
SPEC.loader.exec_module(vector_scale_eval)


class FakeStore:
    def __init__(self, suffix: str, create: bool = True):
        del suffix, create
        self.records = {}

    def upsert(self, records):
        self.records.update({record.record_id: record for record in records})

    def search(self, query):
        return vector_scale_eval.reference_search(list(self.records.values()), query)

    def close(self, cleanup):
        del cleanup


def test_corpus_and_queries_are_deterministic():
    first = vector_scale_eval.make_corpus(20)
    second = vector_scale_eval.make_corpus(20)

    assert first == second
    assert len(first) == 20
    assert len(vector_scale_eval.make_queries(first)) == 4
    assert all(len(record.vector) == 3 for record in first)


def test_fake_provider_passes_bounded_scale_and_mixed_load():
    result = vector_scale_eval._run_provider(
        "fake", FakeStore, [20], workers=2, operations=8, cleanup=True
    )

    assert result["ok"] is True
    size_result = result["sizes"][0]
    assert size_result["ok"] is True
    assert size_result["mixed_load"]["successful_operations"] == 8
    assert size_result["mixed_load"]["failed_operations"] == 0


def test_percentiles_keep_tail_measurements():
    summary = vector_scale_eval._percentiles([1.0, 2.0, 3.0, 4.0])

    assert summary["p50"] == 3.0
    assert summary["p95"] == 4.0
    assert summary["p99"] == 4.0
