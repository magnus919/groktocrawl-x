"""Capability discovery for the opt-in experimental research protocol."""

from typing import Any

from fastapi import APIRouter, HTTPException

from common.features import is_enabled

router = APIRouter()

_ROUTE_PREFIX = "/experimental/research/v1"


def capability_document() -> dict[str, Any]:
    """Return the honest capability boundary for the current W6 slice."""
    return {
        "protocol_version": "research/1",
        "route_prefix": _ROUTE_PREFIX,
        "implementation_stage": "contract_and_golden_traces",
        "recovery_mode": "not_advertised",
        "replay": {
            "mode": "contract_only",
            "window_events": 0,
        },
        "operations": {
            "capabilities": {"available": True},
            "runs": {"available": False, "reason": "public_adapters_pending"},
            "artifacts": {"available": False, "reason": "public_adapters_pending"},
            "evidence": {"available": False, "reason": "public_adapters_pending"},
            "sessions": {"available": False, "reason": "public_adapters_pending"},
        },
    }


@router.get(f"{_ROUTE_PREFIX}/capabilities")
async def get_experimental_research_capabilities() -> dict[str, Any]:
    """Advertise the opt-in protocol without implying unavailable operations."""
    if not is_enabled("experimental_research"):
        raise HTTPException(status_code=404, detail="Experimental research disabled")
    return capability_document()
