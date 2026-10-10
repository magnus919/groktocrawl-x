"""The full capture probe identifies the Python worker separately from Tini."""

from __future__ import annotations

import importlib.util
import io
import os
import stat
import sys
import types
from pathlib import Path
from types import SimpleNamespace

import pytest


def _probe():
    path = Path(__file__).resolve().parents[1] / "integration" / "scraper_egress_boundary_probe.py"
    spec = importlib.util.spec_from_file_location("scraper_boundary_probe", path)
    module = importlib.util.module_from_spec(spec)
    package = types.ModuleType("scraper")
    package.__path__ = []
    source_http = types.ModuleType("scraper.source_http")
    source_http.source_httpx_client = lambda: None
    valkey = types.ModuleType("scraper.valkey_control")
    valkey.RESERVE_SLOT_SCRIPT = ""
    valkey.ValkeyControlClient = type("ValkeyControlClient", (), {})
    with pytest.MonkeyPatch.context() as patch:
        patch.setitem(sys.modules, "scraper", package)
        patch.setitem(sys.modules, "scraper.source_http", source_http)
        patch.setitem(sys.modules, "scraper.valkey_control", valkey)
        spec.loader.exec_module(module)
    return module


def _install_processes(monkeypatch, probe, processes):
    monkeypatch.setattr(probe.os, "scandir", lambda _path: [SimpleNamespace(name=str(pid)) for pid in processes])
    monkeypatch.setattr(probe, "open", lambda path, _mode: io.BytesIO(processes[int(path.split("/")[2])]), raising=False)


def test_worker_discovery_excludes_tini_wrapper(monkeypatch):
    probe = _probe()
    interpreter = os.fsencode(sys.executable)
    worker = b"\0".join([interpreter, b"-m", b"scraper.capture_firewall", b""])
    tini = b"\0".join([b"/usr/bin/tini", b"-s", b"-g", b"--", interpreter, b"-m", b"scraper.capture_firewall", b""])
    _install_processes(monkeypatch, probe, {1: tini, 7: worker})
    assert probe._protected_worker_pid() == 7


def test_browser_failure_diagnostics_are_bounded_and_distinguish_private_hit():
    probe = _probe()
    navigation = {
        "success": True,
        "result": {
            "url": "http://flare-origin.test/get",
            "http_status": 200,
        },
    }
    assert probe._navigation_diagnostics(navigation) == (True, True, 200)
    assert probe._marker_diagnostics(
        {
            "result": {
                "script_result": {
                    "fixtureHostMatches": True,
                    "markerExists": True,
                    "markerState": "PRIVATE_TARGET_REACHABLE",
                }
            }
        }
    ) == (True, True, True, "PRIVATE_TARGET_REACHABLE")
    assert probe._marker_diagnostics({"result": {"script_result": "unstructured"}}) == (
        False,
        False,
        False,
        "unknown",
    )
    # Summaries expose only fixed booleans, enum values, and bounded HTTP status;
    # neither response URLs nor page text are returned to CI logs.
    assert probe._navigation_diagnostics(
        {"success": False, "result": {"url": "http://secret.invalid/path", "http_status": 503}}
    ) == (False, False, 503)


def test_control_socket_probe_requires_nonwritable_owner_directories(monkeypatch):
    probe = _probe()
    bindings = (
        ("/run/scraper/app.sock", 10001),
        ("/run/scraper-state/control.sock", 10002),
        ("/run/scraper-llm/control.sock", 10002),
        ("/run/browser-control/controller.sock", 0),
        ("/run/flare-control/control.sock", 10003),
    )
    entries = {}
    for path, uid in bindings:
        entries[path] = SimpleNamespace(
            st_mode=stat.S_IFSOCK | 0o660,
            st_uid=uid,
            st_gid=20000,
        )
        entries[os.path.dirname(path)] = SimpleNamespace(
            st_mode=stat.S_IFDIR | 0o2710,
            st_uid=uid,
            st_gid=20000,
        )
    monkeypatch.setattr(probe.os, "lstat", lambda path: entries[path])
    probe._assert_control_socket_permissions()

    entries["/run/browser-control"].st_mode = stat.S_IFDIR | 0o2770
    with pytest.raises(RuntimeError, match=r"browser-control.*2770.*2710"):
        probe._assert_control_socket_permissions()


@pytest.mark.parametrize("duplicate", [False, True])
def test_worker_discovery_requires_one_exact_python_process(monkeypatch, duplicate):
    probe = _probe()
    worker = b"\0".join([os.fsencode(sys.executable), b"-m", b"scraper.capture_firewall", b""])
    processes = {1: b"/usr/bin/tini\0--\0" + worker}
    if duplicate:
        processes.update({7: worker, 8: worker})
    _install_processes(monkeypatch, probe, processes)
    with pytest.raises(RuntimeError, match="unique protected scraper worker"):
        probe._protected_worker_pid()
