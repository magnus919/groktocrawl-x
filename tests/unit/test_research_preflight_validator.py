"""Fail-closed comparison preflight validator tests."""

import importlib.util
import json
from pathlib import Path

SCRIPT = Path(__file__).parents[2] / "scripts/validate-research-preflight.py"
SPEC = importlib.util.spec_from_file_location("preflight_validator", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def draft() -> dict:
    return json.loads(
        (Path(__file__).parents[2] / "docs/experiments/research-preflight.json").read_text()
    )


def test_frozen_candidate_preflight_still_requires_comparison_authorization():
    errors = MODULE.validate_manifest(draft(), Path(__file__).parents[2])
    assert errors == ["comparison_authorized is false"]


def test_missing_file_pin_is_rejected_without_reading_arbitrary_paths():
    manifest = draft()
    manifest["file_pins"] = [{"path": "missing.json", "sha256": "0" * 64}]
    errors = MODULE.validate_manifest(manifest, Path(__file__).parents[2])
    assert "file_pins[0] target is missing" in errors


def test_unsafe_file_pin_is_rejected():
    manifest = draft()
    manifest["file_pins"] = [{"path": "../secret", "sha256": "0" * 64}]
    errors = MODULE.validate_manifest(manifest, Path(__file__).parents[2])
    assert "file_pins[0].path is unsafe" in errors
