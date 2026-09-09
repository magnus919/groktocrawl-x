"""Unit tests for the fail-open pgvector shadow adapter."""

import importlib.util
import sys
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).parents[2] / "semantic-svc" / "shadow_pgvector.py"
SPEC = importlib.util.spec_from_file_location("shadow_pgvector_under_test", MODULE_PATH)
assert SPEC and SPEC.loader
shadow = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = shadow
SPEC.loader.exec_module(shadow)


def test_default_mode_keeps_shadow_disabled(monkeypatch):
    monkeypatch.delenv("VECTOR_STORE_MODE", raising=False)
    monkeypatch.delenv("PGVECTOR_SHADOW_DSN", raising=False)

    config = shadow.ShadowConfig.from_env()

    assert config.mode == "qdrant"
    assert config.enabled is False


def test_shadow_mode_requires_dsn(monkeypatch):
    monkeypatch.setenv("VECTOR_STORE_MODE", "shadow_pgvector")
    monkeypatch.delenv("PGVECTOR_SHADOW_DSN", raising=False)

    with pytest.raises(ValueError, match="PGVECTOR_SHADOW_DSN"):
        shadow.ShadowConfig.from_env()


def test_shadow_sample_rate_is_bounded(monkeypatch):
    monkeypatch.setenv("VECTOR_STORE_MODE", "shadow_pgvector")
    monkeypatch.setenv("PGVECTOR_SHADOW_DSN", "postgresql://shadow")
    monkeypatch.setenv("PGVECTOR_SHADOW_SAMPLE_RATE", "1.1")

    with pytest.raises(ValueError, match="between 0 and 1"):
        shadow.ShadowConfig.from_env()


def test_comparison_reports_identity_and_score_match():
    candidate = [
        shadow.ShadowSearchResult(11, "https://one", "One", 0.9),
        shadow.ShadowSearchResult(12, "https://two", "Two", 0.8),
    ]

    result = shadow.compare_results(
        [(11, 0.90001), (12, 0.79999)], candidate, score_tolerance=0.0001
    )

    assert result.matches is True
    assert result.maximum_score_delta == pytest.approx(0.00001)


def test_comparison_rejects_reordered_identity_even_when_scores_match():
    candidate = [
        shadow.ShadowSearchResult(12, "https://two", "Two", 0.9),
        shadow.ShadowSearchResult(11, "https://one", "One", 0.8),
    ]

    result = shadow.compare_results(
        [(11, 0.9), (12, 0.8)], candidate, score_tolerance=0.0001
    )

    assert result.matches is False
    assert result.authoritative_ids == (11, 12)
    assert result.shadow_ids == (12, 11)


def test_vector_literal_preserves_full_float_precision():
    assert shadow._vector_literal([0.1, -0.25, 1]) == "[0.10000000000000001,-0.25,1]"
