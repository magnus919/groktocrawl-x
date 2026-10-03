import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
SPEC = importlib.util.spec_from_file_location(
    "run_slsa_replay_pilot", ROOT / "scripts/run_slsa_replay_pilot.py"
)
runner = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = runner
SPEC.loader.exec_module(runner)
PACKET = ROOT / "docs/experiments/typesafe-jev/slsa-replay-2026-10-03.case-packet.json"


def test_runner_rejects_mutated_packet_before_call(tmp_path):
    packet = json.loads(PACKET.read_text())
    packet["cases"].append(packet["cases"][0])
    mutated = tmp_path / "mutated.json"
    mutated.write_text(json.dumps(packet))
    marker = tmp_path / "called"
    proxy = tmp_path / "proxy.py"
    proxy.write_text(f"from pathlib import Path; Path({str(marker)!r}).touch()\n")
    try:
        runner.run(mutated, tmp_path, [sys.executable, str(proxy)])
    except ValueError as error:
        assert "digest" in str(error)
    else:
        raise AssertionError("mutated packet must be rejected")
    assert not marker.exists()


def test_call_receipt_allowlists_provider_fields(tmp_path):
    state = json.loads(PACKET.read_text())["cases"][0]["state"]
    plan = runner.builder.build_sufficiency_request(state)
    assert isinstance(plan, runner.builder.RequestPlan)
    fake = tmp_path / "fake_provider.py"
    fake.write_text(
        """import json, sys
r=json.loads(sys.stdin.buffer.read())
qid=next(iter(r['questions']))
print(json.dumps({'model':'jev-1.13.0','answers':{qid:{'type':'noul','noul':0.9}},
 '_elapsed_ms':4.5,'usage':{'input_tokens':7,'output_tokens':3,'private':'LEAK'},
 'response_text':'MUST_NOT_ESCAPE'}))
"""
    )
    receipt, validated = runner._call([sys.executable, str(fake)], plan)
    assert isinstance(validated, runner.builder.ValidatedNoulResponse)
    assert receipt["elapsed_ms"] == 4.5
    assert receipt["usage"] == {"input_tokens": 7, "output_tokens": 3}
    encoded = json.dumps(receipt)
    assert "LEAK" not in encoded and "MUST_NOT_ESCAPE" not in encoded
    assert receipt["response_sha256"] == hashlib.sha256(
        subprocess.run([sys.executable, str(fake)], input=plan.serialized,
                       capture_output=True, check=True).stdout
    ).hexdigest()


def test_existing_output_path_fails_before_proxy_or_call(tmp_path):
    output = tmp_path / "results.json"
    output.write_text("preserve")
    marker = tmp_path / "called"
    proxy = tmp_path / "proxy.py"
    proxy.write_text(f"from pathlib import Path; Path({str(marker)!r}).touch()\n")
    process = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_slsa_replay_pilot.py"),
            "--packet", str(PACKET),
            "--corpus", str(tmp_path),
            "--output", str(output),
            "--", sys.executable, str(proxy),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert process.returncode != 0
    assert output.read_text() == "preserve"
    assert not marker.exists()
