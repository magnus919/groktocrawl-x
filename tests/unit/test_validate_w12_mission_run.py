import importlib.util
from pathlib import Path

SCRIPT = Path("scripts/validate_w12_mission_run.py")
SPEC = importlib.util.spec_from_file_location("validate_w12_mission_run", SCRIPT)
assert SPEC and SPEC.loader
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)


def test_validator_rejects_an_empty_run(tmp_path):
    assert validator.validate_run(tmp_path, expected_revision="a" * 40) == [
        "run manifest or summary is missing"
    ]
