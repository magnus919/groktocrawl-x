#!/usr/bin/env python3
"""Run the frozen incumbent gap prompt sequentially through an operator proxy.

The control arm sends only the four packet-frozen messages, never the evaluator
pool. It records digests and parsed recommendations, not raw model responses.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any

PACKET_SHA256 = "bf080316bf2470d068b7207df4718971a385dbcc517450f802728a062815bea9"
CASE_COUNT = 4
MODEL_ALIAS = "free"


def _safe_model(value: Any) -> str | None:
    if isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9._:/-]{1,128}", value):
        return value
    return None


def _parse_content(content: str) -> tuple[str, list[str] | None]:
    cleaned = content.strip().removeprefix("```json").removesuffix("```").strip()
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        return "invalid_json", None
    if not isinstance(parsed, list) or len(parsed) > 5:
        return "invalid_shape", None
    topics = [value[:500] for value in parsed if isinstance(value, str)]
    return "valid_json_array", topics


def run(packet_path: Path, proxy: list[str]) -> dict[str, Any]:
    raw = packet_path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != PACKET_SHA256:
        raise ValueError("case packet digest differs from signed freeze")
    packet = json.loads(raw)
    if (packet.get("schema_version") != "jev-slsa-replay-pilot/2"
            or packet.get("study_id") != "jev-slsa-deterministic-replay-2026-10-03"
            or len(packet.get("cases", [])) != CASE_COUNT
            or packet.get("call_budget", {}).get("incumbent_control_max_total_requests") != CASE_COUNT):
        raise ValueError("unsupported packet or incumbent budget")
    outcomes = []
    for case in packet["cases"]:
        control = case["incumbent_gap_control"]
        prompt = control["user_prompt"]
        if hashlib.sha256(prompt.encode()).hexdigest() != control["prompt_sha256"]:
            raise ValueError("frozen incumbent prompt digest mismatch")
        payload = {
            "model": MODEL_ALIAS,
            "messages": [
                {"role": "system", "content": control["system_prompt"]},
                {"role": "user", "content": prompt},
            ],
        }
        request = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()
        try:
            process = subprocess.run(proxy, input=request, capture_output=True, timeout=105, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            outcomes.append({"case_id": case["case_id"], "status": "proxy_or_timeout_failure", "error_type": type(exc).__name__})
            continue
        if process.returncode:
            outcomes.append({"case_id": case["case_id"], "status": "proxy_process_failure", "returncode": process.returncode})
            continue
        response_hash = hashlib.sha256(process.stdout).hexdigest()
        try:
            response = json.loads(process.stdout)
        except (json.JSONDecodeError, UnicodeDecodeError):
            outcomes.append({"case_id": case["case_id"], "status": "invalid_proxy_json", "response_sha256": response_hash})
            continue
        if response.get("error"):
            outcomes.append({
                "case_id": case["case_id"], "status": "proxy_or_provider_failure",
                "error_type": response["error"] if response["error"] in {
                    "provider_http", "proxy_transport", "TimeoutError", "URLError"
                } else "unspecified_proxy_error",
                "response_sha256": response_hash,
            })
            continue
        try:
            content = response["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            outcomes.append({"case_id": case["case_id"], "status": "invalid_response_shape", "response_sha256": response_hash})
            continue
        if not isinstance(content, str):
            outcomes.append({"case_id": case["case_id"], "status": "invalid_content_type", "response_sha256": response_hash})
            continue
        status, topics = _parse_content(content)
        outcome: dict[str, Any] = {
            "case_id": case["case_id"], "status": status,
            "response_sha256": response_hash,
            "requested_alias": MODEL_ALIAS,
            "returned_model": _safe_model(response.get("model")),
            "returned_alias": response.get("_configured_model_alias") if response.get("_configured_model_alias") == MODEL_ALIAS else None,
            "elapsed_ms": response.get("_elapsed_ms") if isinstance(response.get("_elapsed_ms"), (int, float)) and not isinstance(response.get("_elapsed_ms"), bool) and 0 <= response["_elapsed_ms"] < 1e9 else None,
        }
        if topics is not None:
            outcome["recommendation_only"] = True
            outcome["topics"] = topics
        outcomes.append(outcome)
    return {
        "study_id": packet["study_id"], "case_packet_sha256": digest,
        "requested_model_alias": MODEL_ALIAS, "calls_attempted": len(outcomes),
        "calls_evaluated": sum(x["status"] == "valid_json_array" for x in outcomes),
        "searches_dispatched": 0, "outcomes": outcomes,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("proxy", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if args.proxy and args.proxy[0] == "--":
        args.proxy = args.proxy[1:]
    if not args.proxy:
        parser.error("supply an operator-configured proxy command after --")
    fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "w+", encoding="utf-8") as out:
        out.write('{"status":"running_incomplete"}\n')
        out.flush()
        os.fsync(out.fileno())
        try:
            result = run(args.packet, args.proxy)
        except Exception as exc:
            out.seek(0)
            out.truncate()
            out.write(json.dumps({"status": "failed_incomplete", "error_type": type(exc).__name__}) + "\n")
            out.flush()
            os.fsync(out.fileno())
            raise
        out.seek(0)
        out.truncate()
        out.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
        out.flush()
        os.fsync(out.fileno())
    print(json.dumps({"calls_attempted": result["calls_attempted"], "calls_evaluated": result["calls_evaluated"], "searches_dispatched": 0}))

if __name__ == "__main__":
    main()
