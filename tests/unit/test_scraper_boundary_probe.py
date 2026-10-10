"""The full capture probe identifies the Python worker separately from Tini."""

from __future__ import annotations

import importlib.util
import io
import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


def _probe():
    path = Path(__file__).resolve().parents[1] / "integration" / "scraper_egress_boundary_probe.py"
    spec = importlib.util.spec_from_file_location("scraper_boundary_probe", path)
    module = importlib.util.module_from_spec(spec)
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
