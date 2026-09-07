"""The experimental capability adapter advertises only implemented behavior."""

from agent.routes.experimental_research import (
    capability_document,
    router,
)
from fastapi import FastAPI
from fastapi.testclient import TestClient


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_capabilities_are_hidden_by_default(monkeypatch) -> None:
    monkeypatch.delenv("FEATURE_EXPERIMENTAL_RESEARCH", raising=False)
    response = _client().get("/experimental/research/v1/capabilities")
    assert response.status_code == 404


def test_capabilities_report_contract_only_stage(monkeypatch) -> None:
    monkeypatch.setenv("FEATURE_EXPERIMENTAL_RESEARCH", "true")
    response = _client().get("/experimental/research/v1/capabilities")
    assert response.status_code == 200
    payload = response.json()
    assert payload == capability_document()
    assert payload["implementation_stage"] == "contract_and_golden_traces"
    assert payload["recovery_mode"] == "not_advertised"
    assert payload["operations"]["runs"]["available"] is False
