"""Candidate deployment contracts for Parse and semantic timeout wiring."""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def _candidate_services() -> dict:
    compose = yaml.safe_load((ROOT / "compose.experimental-candidate.yml").read_text())
    return compose["services"]


def test_candidate_parse_service_is_private_and_addressable_by_agent() -> None:
    services = _candidate_services()
    parse = services["candidate-parse"]
    assert "ports" not in parse
    assert parse["build"]["dockerfile"] == "parse-svc/Dockerfile"
    aliases = parse["networks"]["candidate_private"]["aliases"]
    assert aliases == ["parse-svc"]
    assert (
        services["candidate-agent"]["depends_on"]["candidate-parse"]["condition"]
        == "service_healthy"
    )


def test_candidate_agent_receives_bounded_semantic_timeout() -> None:
    environment = _candidate_services()["candidate-agent"]["environment"]
    assert environment["SEMANTIC_CLIENT_TIMEOUT_SECONDS"] == (
        "${SEMANTIC_CLIENT_TIMEOUT_SECONDS:-60}"
    )
