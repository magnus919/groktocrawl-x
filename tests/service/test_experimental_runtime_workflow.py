"""Validate the experimental CI execution boundary and required-check outcomes."""

import itertools
import os
import subprocess
from pathlib import Path

import pytest
import yaml

from scripts.classify_ci_changes import requires_full_runtime, requires_twin_contracts

ROOT = Path(__file__).parents[2]
WORKFLOW = yaml.safe_load((ROOT / ".github/workflows/runtime.yml").read_text())


def test_runtime_workflow_has_no_publishing_or_privileged_execution():
    triggers = WORKFLOW.get("on", WORKFLOW.get(True))
    assert set(triggers) == {"pull_request", "push"}
    assert WORKFLOW["permissions"] == {"contents": "read"}
    assert "secrets." not in repr(WORKFLOW)
    assert set(WORKFLOW["jobs"]) == {
        "changes",
        "twin-contracts",
        "integration-tests",
        "runtime-gate",
    }
    for job in WORKFLOW["jobs"].values():
        assert job["runs-on"] == "ubuntu-latest"
        assert 0 < job["timeout-minutes"] <= 60
        assert job.get("permissions", WORKFLOW["permissions"]) == {"contents": "read"}
        for step in job["steps"]:
            if step.get("uses", "").startswith("actions/checkout@"):
                assert step["with"]["persist-credentials"] is False
            assert "docker/login-action" not in step.get("uses", "")
            assert "docker push" not in step.get("run", "")


def test_stack_is_built_locally_with_fixture_search_and_owned_volumes():
    base = yaml.safe_load((ROOT / "docker-compose.yml").read_text())
    override = yaml.safe_load((ROOT / "docker-compose.ci.yml").read_text())
    for name, service in base["services"].items():
        if "build" in service:
            assert override["services"][name]["image"].startswith("groktocrawl-x-ci/")
    search = override["services"]["slopsearx"]
    assert search["build"] == base["services"]["slopsearx-fixture"]["build"]
    assert search["healthcheck"] == base["services"]["slopsearx-fixture"]["healthcheck"]
    assert override["volumes"]["hf-cache"]["external"] is False
    job = WORKFLOW["jobs"]["integration-tests"]
    assert job["env"]["COMPOSE_FILE"] == "docker-compose.yml:docker-compose.ci.yml"
    commands = "\n".join(step.get("run", "") for step in job["steps"])
    assert "--profile indexing --profile fixture build" in commands
    assert "up -d --no-build --pull never" in commands
    assert "pull --ignore-buildable" in commands
    assert "LLM_BASE_URL=http://llm-svc:8011/v1?run_id=" in commands
    assert "docker rm -f" not in commands
    assert "down --volumes --remove-orphans" in commands


@pytest.mark.parametrize(
    ("classification", "runtime_required", "twin_required", "runtime", "twin"),
    list(
        itertools.product(
            ["success", "failure", "cancelled", "skipped"],
            ["true", "false", ""],
            ["true", "false", ""],
            ["success", "failure", "cancelled", "skipped"],
            ["success", "failure", "cancelled", "skipped"],
        )
    ),
)
def test_runtime_gate_fails_closed(
    classification, runtime_required, twin_required, runtime, twin
):
    gate = WORKFLOW["jobs"]["runtime-gate"]
    assert gate["if"] == "always()"
    assert set(gate["needs"]) == {"changes", "twin-contracts", "integration-tests"}
    step = gate["steps"][0]
    result = subprocess.run(
        ["bash", "-c", step["run"]],
        env={
            **os.environ,
            "CLASSIFICATION": classification,
            "RUNTIME_REQUIRED": runtime_required,
            "TWIN_REQUIRED": twin_required,
            "RUNTIME_RESULT": runtime,
            "TWIN_RESULT": twin,
        },
        capture_output=True,
        timeout=5,
        check=False,
    )
    expected = (
        classification == "success"
        and runtime_required in {"true", "false"}
        and twin_required in {"true", "false"}
        and (runtime_required == "false" or runtime == "success")
        and (twin_required == "false" or twin == "success")
    )
    assert (result.returncode == 0) is expected


@pytest.mark.parametrize(
    "path", [".github/workflows/runtime.yml", "docker-compose.ci.yml"]
)
def test_runtime_configuration_changes_require_both_test_lanes(path):
    assert requires_full_runtime([path])
    assert requires_twin_contracts([path])
