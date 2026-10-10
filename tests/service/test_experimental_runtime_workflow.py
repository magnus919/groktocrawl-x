"""Validate the experimental CI execution boundary and required-check outcomes."""

import ipaddress
import itertools
import os
import re
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
        "research-storage",
        "protected-browser-profile",
        "protected-flare-profile",
        "protected-capture-composition",
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
    assert "scripts/ci_public_image_prefetch.py" in commands
    assert "--group runtime" in commands
    assert "--profile indexing" in commands
    assert "--profile fixture" in commands
    assert "LLM_BASE_URL=http://llm-svc:8011/v1?run_id=" in commands
    assert "docker rm -f" not in commands
    assert "down --volumes --remove-orphans" in commands


def test_protected_browser_profile_is_required_by_runtime_gate():
    profile = WORKFLOW["jobs"]["protected-browser-profile"]
    gate = WORKFLOW["jobs"]["runtime-gate"]
    assert profile["needs"] == "changes"
    assert "needs.changes.outputs.requires_full_runtime == 'true'" in profile["if"]
    assert "protected-browser-profile" in gate["needs"]
    assert "BROWSER_PROFILE_RESULT" in gate["steps"][0]["env"]
    assert 'test "$BROWSER_PROFILE_RESULT" = success' in gate["steps"][0]["run"]
    steps = profile["steps"]
    controller_probe = next(step for step in steps if step.get("name") == "Verify renderer network boundary from the controller API")
    renderer_probe = next(step for step in steps if step.get("name") == "Verify renderer firewall and privilege drop in its namespace")
    assert "docker compose exec -T --user 10002:20000 candidate-browser-controller" in controller_probe["run"]
    assert "browser_capture_boundary_probe.py" in controller_probe["run"]
    assert "docker compose exec -T candidate-browser-renderer" in renderer_probe["run"]
    assert "browser_renderer_isolation_probe.py" in renderer_probe["run"]


def test_protected_flare_profile_is_required_by_runtime_gate():
    profile = WORKFLOW["jobs"]["protected-flare-profile"]
    gate = WORKFLOW["jobs"]["runtime-gate"]
    assert profile["needs"] == "changes"
    assert "needs.changes.outputs.requires_full_runtime == 'true'" in profile["if"]
    assert "protected-flare-profile" in gate["needs"]
    assert "PROTECTED_FLARE_RESULT" in gate["steps"][0]["env"]
    assert 'test "$PROTECTED_FLARE_RESULT" = success' in gate["steps"][0]["run"]
    assert "protected-capture-composition" in gate["needs"]
    assert "PROTECTED_CAPTURE_RESULT" in gate["steps"][0]["env"]
    assert 'test "$PROTECTED_CAPTURE_RESULT" = success' in gate["steps"][0]["run"]
    steps = profile["steps"]
    probe = next(step for step in steps if step.get("name", "").startswith("Exercise upstream Flare"))
    assert "tests/integration/protected_flare_api_probe.py" in probe["run"]
    assert "docker compose --profile protected-flare exec -T --user 10001:20000 candidate-scraper" in probe["run"]
    assert any("candidate-flare-test-origin" in step.get("run", "") for step in steps)
    init = yaml.safe_load((ROOT / "compose.experimental-candidate.yml").read_text())["services"]
    for service_name in ("candidate-scraper-socket-init", "candidate-flare-control-socket-init"):
        socket_init = init[service_name]
        assert socket_init["user"] == "0:0"
        assert socket_init["cap_drop"] == ["ALL"]
        assert set(socket_init["cap_add"]) == {"CHOWN", "FOWNER", "FSETID"}
        assert "stat -c '%u:%g:%a'" in " ".join(socket_init["command"])
    diagnostic = next(step for step in steps if step.get("name") == "Collect bounded protected Flare startup diagnostics")
    assert "candidate-scraper-socket-init" in diagnostic["run"]
    assert "candidate-flare-control-socket-init" in diagnostic["run"]


def test_capture_composition_runs_real_ingress_scrape_meta_and_network_probes():
    job = WORKFLOW["jobs"]["protected-capture-composition"]
    assert job["needs"] == "changes"
    assert "requires_full_runtime == 'true'" in job["if"]
    steps = job["steps"]
    start = next(step for step in steps if step.get("name") == "Build and start the isolated service composition")
    assert "candidate-capture-peer-sentinel" in start["run"]
    assert "candidate-host-bridge-sentinel" in start["run"]
    diagnostics = next(step for step in steps if step.get("name") == "Collect bounded composition diagnostics")
    assert "candidate-scraper-socket-init" in diagnostics["run"]
    assert "candidate-flare-control-socket-init" in diagnostics["run"]
    ingress = next(step for step in steps if step.get("name") == "Verify the fixed agent-to-scraper HTTP ingress bridge")
    assert "docker compose exec -T candidate-private-sentinel" in ingress["run"]
    assert "scraper_ingress_boundary_probe.py" in ingress["run"]
    egress = next(step for step in steps if step.get("name") == "Verify direct scraper network denial and fixed model/source brokers")
    assert "docker compose exec -T --user 10001:20000 candidate-scraper" in egress["run"]
    assert "scraper_egress_boundary_probe.py" in egress["run"]
    ingress_source = (ROOT / "tests/integration/scraper_ingress_boundary_probe.py").read_text()
    assert '"/scrape"' in ingress_source and '"/scrape/meta"' in ingress_source
    assert "force_browser" in ingress_source
    egress_source = (ROOT / "tests/integration/scraper_egress_boundary_probe.py").read_text()
    for capability in ("cache", "robots", "rate", "clearance"):
        assert f'"{capability}"' in egress_source
    assert "RESERVE_SLOT_SCRIPT" in egress_source
    compose = yaml.safe_load((ROOT / "compose.protected-capture-ci.yml").read_text())
    assert compose["services"]["candidate-capture-peer-sentinel"]["networks"]["candidate_capture"]["ipv4_address"] == "172.31.254.6"
    assert compose["services"]["candidate-host-bridge-sentinel"]["network_mode"] == "host"
    assert '"degraded"' not in ingress_source
    sentinel_check = next(
        step for step in steps if step.get("name") == "Verify hostile JavaScript did not reach the private sentinel"
    )
    assert sentinel_check["if"] == "always()"
    assert "p.is_file()" in sentinel_check["run"]
    assert "private_sentinel_hits=" in sentinel_check["run"]
    assert "assert not lines" in sentinel_check["run"]


def test_fixture_subnet_static_addresses_avoid_gateway_and_collisions():
    assignments: dict[tuple[str, str], str] = {}
    network_subnets: dict[str, ipaddress.IPv4Network] = {}
    for filename in ("compose.protected-flare-ci.yml", "compose.protected-capture-ci.yml"):
        document = yaml.safe_load((ROOT / filename).read_text())
        for network_name, network in document.get("networks", {}).items():
            for config in network.get("ipam", {}).get("config", []):
                if "subnet" in config:
                    subnet = ipaddress.ip_network(config["subnet"])
                    previous = network_subnets.setdefault(network_name, subnet)
                    assert previous == subnet
        for service_name, service in document.get("services", {}).items():
            for network_name, config in service.get("networks", {}).items():
                if isinstance(config, dict) and "ipv4_address" in config:
                    key = (service_name, network_name)
                    address = config["ipv4_address"]
                    previous = assignments.setdefault(key, address)
                    assert previous == address

    fixture_network = "candidate_flare_fixture"
    subnet = network_subnets[fixture_network]
    gateway = next(subnet.hosts())
    used = {
        key: ipaddress.ip_address(address)
        for key, address in assignments.items()
        if key[1] == fixture_network
    }
    assert len(used) >= 2
    assert len(set(used.values())) == len(used), "fixture services share a static IP"
    for service, address in used.items():
        assert address in subnet, f"{service[0]} address is outside fixture subnet"
        assert address != gateway, f"{service[0]} collides with Docker's subnet gateway"
        assert address != subnet.broadcast_address


def test_compose_image_digests_are_full_sha256_values():
    compose_files = [*ROOT.glob("compose*.yml"), *ROOT.glob("docker-compose*.yml")]
    assert compose_files
    for path in compose_files:
        for line_number, line in enumerate(path.read_text().splitlines(), start=1):
            if not re.match(r"\s*image:\s*", line):
                continue
            image = line.split("image:", 1)[1].strip().strip("\"'")
            if "@sha256:" in image:
                digest = image.rsplit("@sha256:", 1)[1]
                assert re.fullmatch(r"[0-9a-f]{64}", digest), (
                    f"{path.name}:{line_number} has malformed SHA-256 image pin"
                )


def test_protected_browser_failure_logs_are_bounded_and_precede_teardown():
    steps = WORKFLOW["jobs"]["protected-browser-profile"]["steps"]
    diagnostics = next(
        index
        for index, step in enumerate(steps)
        if step.get("name") == "Collect bounded protected-profile startup diagnostics"
    )
    teardown = next(
        index
        for index, step in enumerate(steps)
        if step.get("name") == "Tear down protected browser profile"
    )
    step = steps[diagnostics]
    assert step["if"] == "failure()"
    assert diagnostics < teardown
    assert "docker compose ps -a" in step["run"]
    assert "docker compose logs --no-color --tail=100" in step["run"]
    assert "docker inspect --format" in step["run"]
    assert ".State.Health" in step["run"]
    assert "env" not in step["run"]
    assert ".Config.Env" not in step["run"]


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
    assert set(gate["needs"]) == {
        "changes",
        "twin-contracts",
        "integration-tests",
        "research-storage",
        "protected-browser-profile",
        "protected-flare-profile",
        "protected-capture-composition",
    }
    step = gate["steps"][0]
    result = subprocess.run(
        ["bash", "-c", step["run"]],
        env={
            **os.environ,
            "CLASSIFICATION": classification,
            "RUNTIME_REQUIRED": runtime_required,
            "TWIN_REQUIRED": twin_required,
            "RUNTIME_RESULT": runtime,
            "BROWSER_PROFILE_RESULT": "success",
            "PROTECTED_FLARE_RESULT": "success",
            "PROTECTED_CAPTURE_RESULT": "success",
            "TWIN_RESULT": twin,
            "STORAGE_RESULT": "success",
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


@pytest.mark.parametrize("profile_result", ["failure", "cancelled", "skipped"])
def test_required_browser_profile_failure_or_skip_fails_runtime_gate(profile_result):
    gate = WORKFLOW["jobs"]["runtime-gate"]
    step = gate["steps"][0]
    result = subprocess.run(
        ["bash", "-c", step["run"]],
        env={
            **os.environ,
            "CLASSIFICATION": "success",
            "RUNTIME_REQUIRED": "true",
            "TWIN_REQUIRED": "false",
            "RUNTIME_RESULT": "success",
            "BROWSER_PROFILE_RESULT": profile_result,
            "TWIN_RESULT": "skipped",
            "STORAGE_RESULT": "success",
        },
        capture_output=True,
        timeout=5,
        check=False,
    )
    assert result.returncode != 0


@pytest.mark.parametrize("profile_result", ["failure", "cancelled", "skipped"])
def test_required_flare_profile_failure_or_skip_fails_runtime_gate(profile_result):
    gate = WORKFLOW["jobs"]["runtime-gate"]
    result = subprocess.run(
        ["bash", "-c", gate["steps"][0]["run"]],
        env={
            **os.environ,
            "CLASSIFICATION": "success",
            "RUNTIME_REQUIRED": "true",
            "TWIN_REQUIRED": "false",
            "RUNTIME_RESULT": "success",
            "BROWSER_PROFILE_RESULT": "success",
            "PROTECTED_FLARE_RESULT": profile_result,
            "PROTECTED_CAPTURE_RESULT": "success",
            "TWIN_RESULT": "skipped",
            "STORAGE_RESULT": "success",
        },
        capture_output=True,
        timeout=5,
        check=False,
    )
    assert result.returncode != 0


def test_documentation_only_change_allows_skipped_browser_profile():
    gate = WORKFLOW["jobs"]["runtime-gate"]
    step = gate["steps"][0]
    result = subprocess.run(
        ["bash", "-c", step["run"]],
        env={
            **os.environ,
            "CLASSIFICATION": "success",
            "RUNTIME_REQUIRED": "false",
            "TWIN_REQUIRED": "false",
            "RUNTIME_RESULT": "skipped",
            "BROWSER_PROFILE_RESULT": "skipped",
            "PROTECTED_FLARE_RESULT": "skipped",
            "PROTECTED_CAPTURE_RESULT": "skipped",
            "TWIN_RESULT": "skipped",
            "STORAGE_RESULT": "skipped",
        },
        capture_output=True,
        timeout=5,
        check=False,
    )
    assert result.returncode == 0


@pytest.mark.parametrize("profile_result", ["failure", "cancelled", "skipped"])
def test_required_capture_profile_failure_or_skip_fails_runtime_gate(profile_result):
    gate = WORKFLOW["jobs"]["runtime-gate"]
    result = subprocess.run(
        ["bash", "-c", gate["steps"][0]["run"]],
        env={
            **os.environ,
            "CLASSIFICATION": "success",
            "RUNTIME_REQUIRED": "true",
            "TWIN_REQUIRED": "false",
            "RUNTIME_RESULT": "success",
            "BROWSER_PROFILE_RESULT": "success",
            "PROTECTED_FLARE_RESULT": "success",
            "PROTECTED_CAPTURE_RESULT": profile_result,
            "TWIN_RESULT": "skipped",
            "STORAGE_RESULT": "success",
        },
        capture_output=True,
        timeout=5,
        check=False,
    )
    assert result.returncode != 0


@pytest.mark.parametrize(
    "path", [".github/workflows/runtime.yml", "docker-compose.ci.yml"]
)
def test_runtime_configuration_changes_require_both_test_lanes(path):
    assert requires_full_runtime([path])
    assert requires_twin_contracts([path])


def test_targeted_session_contracts_use_reachable_compose_fixture():
    steps = WORKFLOW["jobs"]["integration-tests"]["steps"]
    step = next(
        item
        for item in steps
        if item.get("name") == "Run targeted source-backed agent contracts"
    )
    assert "TEST_SITE_BASE_URL=http://test-site:8000" in step["run"]
    assert "test_session_search_zero_results_val_ses_085" in step["run"]
    assert "test_cross_concurrent_session_isolation_val_cross_018" in step["run"]
