"""Parse route handlers — file upload and content extraction."""

import logging
import uuid
from typing import Any

import httpx
from fastapi import APIRouter, Request

from ..exceptions import InvalidRequestError, NotFoundError, UpstreamError
from ..models import ParseResponse, ParseUploadUrlResponse

logger = logging.getLogger(__name__)

router = APIRouter()

PARSE_SVC_URL = "http://parse-svc:8013"
PARSE_UPLOAD_TTL = 3 * 60 * 60  # 3 hours, matches parse-svc/config.py

# Lua script: atomically get and delete the upload data.
# Prevents race conditions where two concurrent parse requests
# with the same upload_id both retrieve and process the file.
_ATOMIC_GETDEL_SCRIPT = """
local data = redis.call('GET', KEYS[1])
if data then
    local content_type = redis.call('GET', KEYS[2])
    local filename = redis.call('GET', KEYS[3])
    redis.call('DEL', KEYS[1], KEYS[2], KEYS[3], KEYS[4])
    return {data, content_type or false, filename or false}
end
return nil
"""


def _consume_upload(r: Any, upload_id: str) -> tuple[bytes, str, str] | None:
    """Atomically consume staged bytes and the metadata needed to parse them."""
    keys = [
        f"parse:upload:{upload_id}:data",
        f"parse:upload:{upload_id}:content_type",
        f"parse:upload:{upload_id}:filename",
        f"parse:upload:{upload_id}",
    ]
    consumed = r.register_script(_ATOMIC_GETDEL_SCRIPT)(keys=keys)
    if not consumed:
        return None

    content, content_type_raw, filename_raw = consumed
    content_type = (
        content_type_raw.decode()
        if isinstance(content_type_raw, bytes)
        else "application/octet-stream"
    )
    filename = (
        filename_raw.decode()
        if isinstance(filename_raw, bytes)
        else "uploaded_file"
    )
    return content, content_type, filename


def _parse_upstream_response(resp: httpx.Response) -> Any:
    """Return a successful Parse payload or raise a stable upstream error."""
    try:
        payload = resp.json()
    except Exception as exc:
        raise UpstreamError(
            detail="Parse service returned invalid response",
            details={"status_code": resp.status_code},
        ) from exc
    if resp.status_code >= 400:
        raise UpstreamError(
            detail=str(payload.get("detail", "Parse service request failed")),
            details={"status_code": resp.status_code},
        )
    return payload


@router.post("/v2/parse/upload-url", response_model=ParseUploadUrlResponse)
async def request_parse_upload_url(request: Request) -> ParseUploadUrlResponse:
    """Reserve a bounded, single-use upload slot for staged parsing."""
    from redis import Redis

    upload_id = str(uuid.uuid4())
    r = Redis.from_url("redis://valkey:6379/0", decode_responses=False)
    r.set(f"parse:upload:{upload_id}", b"pending", ex=PARSE_UPLOAD_TTL)
    return ParseUploadUrlResponse(
        upload_id=upload_id,
        upload_url=f"{request.url.scheme}://{request.url.netloc}/v2/parse/upload/{upload_id}",
    )


@router.put("/v2/parse/upload/{upload_id}")
async def upload_parse_file(upload_id: str, request: Request) -> dict[str, Any]:
    """Upload file bytes for a previously requested upload_id.

    Stores the raw bytes, content-type, and filename in Valkey.
    The content-type is read from the ``Content-Type`` request header.
    The filename is read from the ``X-Filename`` request header.
    """
    from redis import Redis

    r = Redis.from_url("redis://valkey:6379/0", decode_responses=False)
    meta = r.get(f"parse:upload:{upload_id}")
    if meta is None:
        raise NotFoundError(
            detail="Upload ID not found or expired",
            details={"upload_id": upload_id},
        )

    raw_body = await request.body()
    if not raw_body:
        raise InvalidRequestError(detail="Empty body — no file data received")

    content_type = request.headers.get("Content-Type", "application/octet-stream")
    filename = request.headers.get("X-Filename", "uploaded_file")

    pipe = r.pipeline()
    pipe.set(f"parse:upload:{upload_id}:data", raw_body, ex=PARSE_UPLOAD_TTL)
    pipe.set(
        f"parse:upload:{upload_id}:content_type", content_type, ex=PARSE_UPLOAD_TTL
    )
    pipe.set(f"parse:upload:{upload_id}:filename", filename, ex=PARSE_UPLOAD_TTL)
    pipe.set(f"parse:upload:{upload_id}", b"uploaded", ex=PARSE_UPLOAD_TTL)
    pipe.execute()

    return {"status": "uploaded", "upload_id": upload_id}


@router.post("/v2/parse", response_model=ParseResponse)
async def parse_file(request: Request) -> Any:
    """Upload a file and get its content as markdown.

    Supports two modes:

    - Direct: multipart form with ``file`` field (small files)
    - Two-step: form field ``upload_id`` referencing a pre-uploaded file

    ``ocr=hosted`` is an explicit opt-in and is forwarded only when the caller
    requests hosted OCR. The parse service remains local-first by default.
    """
    form = await request.form()
    form_ocr = form.get("ocr", "local")
    ocr = form_ocr if isinstance(form_ocr, str) else "local"
    if ocr not in {"local", "hosted"}:
        raise InvalidRequestError(detail="ocr must be 'local' or 'hosted'")

    # Two-step mode: retrieve pre-uploaded file from Valkey
    upload_id_raw = form.get("upload_id")
    upload_id_str = upload_id_raw if isinstance(upload_id_raw, str) else None
    if upload_id_str:
        from redis import Redis

        r = Redis.from_url("redis://valkey:6379/0", decode_responses=False)
        consumed = _consume_upload(r, upload_id_str)
        if consumed is None:
            raise InvalidRequestError(
                detail="Upload data not found or expired",
                details={"upload_id": upload_id_str},
            )
        content, content_type, filename = consumed

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{PARSE_SVC_URL}/parse",
                files={"file": (filename, content, content_type)},
                data={"ocr": ocr},
            )
            return _parse_upstream_response(resp)

    # Direct mode: file in multipart form
    if "file" not in form:
        raise InvalidRequestError(
            detail="No file provided. Use multipart form with 'file' field."
        )

    upload = form["file"]  # type: ignore[union-attr]
    content = await upload.read()  # type: ignore[union-attr]
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            f"{PARSE_SVC_URL}/parse",
            files={
                "file": (
                    upload.filename or "file",  # type: ignore[union-attr]
                    content,
                    upload.content_type or "application/octet-stream",  # type: ignore[union-attr]
                )
            },
            data={"ocr": ocr},
        )
        return _parse_upstream_response(resp)
