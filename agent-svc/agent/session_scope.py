"""Credential-derived session ownership; never accept scope from a payload."""

import hashlib
from typing import Any

from fastapi import Request

from .exceptions import NotFoundError


def request_scope(request: Request) -> str:
    from . import auth

    authorization = request.headers.get("Authorization", "")
    bearer = authorization[7:] if authorization.startswith("Bearer ") else None
    api_key = request.headers.get("X-API-Key")
    # Match authentication's accepted credential, including its X-API-Key
    # fallback when Authorization is present but invalid. Header aliases for
    # one credential must have one ownership scope.
    credential = (
        (bearer if bearer == auth.API_KEY else api_key)
        if auth.AUTH_ENABLED
        else (bearer or api_key)
    )
    return (
        "key:" + hashlib.sha256(credential.encode()).hexdigest()[:32]
        if credential
        else "anonymous"
    )


async def authorize_session(store: Any, session_id: str, request: Request) -> dict:
    session = await store.aget(session_id)
    if session is None or (
        session.get("owner_scope") is not None
        and session["owner_scope"] != request_scope(request)
    ):
        # Do not reveal existence to a foreign principal.
        raise NotFoundError(detail="Session not found or expired")
    return session
