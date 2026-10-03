import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
SPEC = importlib.util.spec_from_file_location(
    "jev_continuation_pilot_runner", ROOT / "scripts/run_jev_continuation_pilot.py"
)
runner = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = runner
SPEC.loader.exec_module(runner)

PACKET = ROOT / "docs/experiments/typesafe-jev/continuation-pilot-2026-10-03.case-packet.json"


def test_runner_sends_only_stage_payloads_and_gates_dependent_stage(tmp_path):
    fake = tmp_path / "fake_provider.py"
    fake.write_text(
        """import json, sys
request = json.loads(sys.stdin.buffer.read())
assert set(request) == {'model', 'state', 'questions'}
state = request['state']
assert 'assistant_reference' not in state and 'research_agent_proposal' not in state
question_id, question = next(iter(request['questions'].items()))
assert question['type'] == 'noul'
instructions = question['instructions']
if isinstance(instructions, dict) and instructions['question'].startswith('Could a bounded search'):
    p = 0.8
elif isinstance(instructions, dict):
    p = 0.9 if state['obligation']['id'] == 'pilot-03' else 0.1
else:
    p = 0.8
print(json.dumps({'model': 'jev-1.13.0', 'answers': {question_id: {'type': 'noul', 'noul': p}}}))
"""
    )
    result = runner.run(PACKET, [sys.executable, str(fake)])
    assert result["requests_attempted"] == result["requests_validated"] == 17
    assert result["requests_unevaluated"] == result["searches_dispatched"] == 0
    rows = {case["case_id"]: case for case in result["cases"]}
    assert rows["pilot-03"]["stage4"]["probabilities"]["n0"] == 0.8
    assert rows["pilot-01"]["stage4"]["status"] == "skipped_by_frozen_binary_argmax"


def test_runner_does_not_retry_or_continue_after_failed_stage(tmp_path):
    fake = tmp_path / "failing_provider.py"
    fake.write_text("import sys; sys.exit(9)\n")
    result = runner.run(PACKET, [sys.executable, str(fake)])
    assert result["requests_attempted"] == 8
    assert result["requests_validated"] == 0
    assert result["requests_unevaluated"] == 8
    assert all(case["stage3"]["status"] == "skipped_after_stage1_failure" for case in result["cases"])
