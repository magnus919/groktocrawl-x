"""Local-script ownership, deadline and audited-terminal integration tests."""

import asyncio

import pytest
from agent.experimental.controller import (
    ControllerLimits,
    OperationSpec,
    ScriptedController,
    ScriptResult,
    ScriptStep,
)
from agent.experimental.execution import Budget
from agent.experimental.publication import (
    FixturePublication,
    FixtureResearch,
    RenderInput,
)

from tests.unit.test_fixture_publication import audited, journey
from tests.unit.test_knowledge_structure import payload  # noqa: F401


@pytest.fixture
def setup(request):
    def build(
        scenario="supported", callbacks=None, limit=3, overall=1, per_op=1, cleanup=0.01
    ):
        research, inputs = journey(
            request.getfixturevalue("payload"),
            "conflicting" if scenario == "partial" else scenario,
        )
        if scenario == "partial":
            data = research.model_dump(mode="json")
            data["questions"].append(
                {
                    "question_id": "agreement",
                    "question": "Do the pages agree?",
                    "status": "answered",
                    "report_claim_id": "c1",
                }
            )
            research = FixtureResearch.model_validate(data)
            updated = []
            for item in inputs:
                raw = item.model_dump(mode="json")
                raw["research"] = research.model_dump(mode="json")
                raw["artifact"]["question_ids"].append("agreement")
                updated.append(RenderInput.model_validate(raw))
            inputs = updated
        publication = FixturePublication.model_validate(audited(inputs))
        calls = []

        async def acquire():
            calls.append("acquire")
            return ScriptResult(output_id="snapshot-ref", actual=Budget(sources=1))

        async def publish():
            calls.append("publish")
            return ScriptResult(
                output_id="set1", actual=Budget(sources=1), publication=publication
            )

        functions = callbacks or [acquire, publish]
        steps = tuple(
            ScriptStep(
                OperationSpec(
                    operation_id=f"op{index}",
                    input_digest="a" * 64,
                    output_id="set1" if index == len(functions) - 1 else "snapshot-ref",
                    reservation=Budget(sources=1),
                ),
                fn,
            )
            for index, fn in enumerate(functions)
        )
        controller = ScriptedController(
            run_id="run1",
            steps=steps,
            budget=Budget(sources=limit),
            limits=ControllerLimits(
                overall_seconds=overall,
                operation_seconds=per_op,
                cleanup_seconds=cleanup,
            ),
            research=research,
            artifact_set_id="set1",
            renderer_version="fixture-render/1",
            auditor=research.verifications.verifier,
        )
        return controller, calls, publication

    return build


@pytest.mark.parametrize(
    "scenario,coverage",
    [
        ("supported", "complete"),
        ("partial", "partial"),
        ("conflicting", "insufficient"),
        ("insufficient", "insufficient"),
    ],
)
async def test_scripted_journey_and_stable_reads(setup, scenario, coverage):
    controller, calls, _ = setup(scenario)
    result = await controller.run()
    assert result.execution_outcome == "completed"
    assert result.answer_coverage == coverage
    assert result.accounting.state == "completed"
    assert result.accounting.spent.sources == 2
    assert result.accounting.reserved.sources == 0
    assert len(result.publication.audits) == 3
    assert calls == ["acquire", "publish"]
    controller.cancel()
    assert await controller.run() is result
    assert calls == ["acquire", "publish"]
    assert "publication" not in result.accounting.model_dump()


async def test_budget_rejects_before_next_dispatch(setup):
    controller, calls, _ = setup(limit=1)
    result = await controller.run()
    assert result.stop_reason == "budget_exhausted"
    assert result.execution_outcome == "failed"
    assert result.publication is None
    assert calls == ["acquire"]


async def test_cancel_before_start_dispatches_nothing(setup):
    controller, calls, _ = setup()
    controller.cancel()
    result = await controller.run()
    assert result.execution_outcome == "cancelled"
    assert calls == []


async def test_cancel_active_child_retains_reservation(setup):
    started = asyncio.Event()
    stopped = asyncio.Event()

    async def work():
        started.set()
        try:
            await asyncio.Event().wait()
        finally:
            stopped.set()

    controller, _, _ = setup(callbacks=[work])
    task = asyncio.create_task(controller.run())
    await started.wait()
    controller.cancel()
    result = await task
    assert stopped.is_set()
    assert result.execution_outcome == "cancelled"
    assert result.accounting.reserved.sources == 1
    assert result.publication is None
    assert not result.cleanup_incomplete


@pytest.mark.parametrize("overall,per_op", [(0.01, 1), (1, 0.01)])
async def test_timeouts_are_terminal_and_keep_unknown_usage(setup, overall, per_op):
    async def work():
        await asyncio.Event().wait()

    controller, _, _ = setup(callbacks=[work], overall=overall, per_op=per_op)
    result = await controller.run()
    assert result.stop_reason == "deadline_exceeded"
    assert result.execution_outcome == "failed"
    assert result.accounting.reserved.sources == 1
    assert result.publication is None


async def test_noncooperative_child_cleanup_is_bounded(setup):
    release = asyncio.Event()
    finished = asyncio.Event()

    async def work():
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            await release.wait()
        finally:
            finished.set()
        raise RuntimeError("late failure must not change terminal result")

    controller, _, _ = setup(callbacks=[work], per_op=0.01, cleanup=0.01)
    try:
        result = await asyncio.wait_for(controller.run(), timeout=0.5)
        assert result.cleanup_incomplete
        assert result.publication is None
    finally:
        release.set()
        await asyncio.wait_for(finished.wait(), timeout=0.5)
        await asyncio.sleep(0)
    assert controller.result is result


async def test_external_task_cancellation_records_terminal_and_reraises(setup):
    started = asyncio.Event()

    async def work():
        started.set()
        await asyncio.Event().wait()

    controller, _, _ = setup(callbacks=[work])
    task = asyncio.create_task(controller.run())
    await started.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert controller.result.execution_outcome == "cancelled"
    assert await controller.run() is controller.result


async def test_concurrent_run_rejected_without_second_dispatch(setup):
    started, release = asyncio.Event(), asyncio.Event()

    async def work():
        started.set()
        await release.wait()
        return ScriptResult(output_id="set1", actual=Budget())

    controller, _, _ = setup(callbacks=[work])
    task = asyncio.create_task(controller.run())
    await started.wait()
    with pytest.raises(RuntimeError, match="already running"):
        await controller.run()
    release.set()
    result = await task
    assert result.stop_reason == "publication_rejected"


@pytest.mark.parametrize(
    "fault",
    ["exception", "identity", "overrun", "invalid_audit", "missing_publication"],
)
async def test_operation_or_audit_failure_never_publishes(setup, fault):
    _, _, publication = setup()

    async def work():
        if fault == "exception":
            raise RuntimeError("fixture failure")
        candidate = publication
        if fault == "invalid_audit":
            data = publication.model_dump(mode="json")
            data["audits"][0]["verdict"] = "fail"
            candidate = FixturePublication.model_validate(data)
        return ScriptResult(
            output_id="wrong" if fault == "identity" else "set1",
            actual=Budget(sources=2 if fault == "overrun" else 1),
            publication=None if fault == "missing_publication" else candidate,
        )

    controller, _, _ = setup(callbacks=[work])
    result = await controller.run()
    assert result.execution_outcome == "failed"
    assert result.accounting.state == "failed"
    assert result.publication is None


async def test_premature_publication_rejected(setup):
    _, _, publication = setup()

    async def early():
        return ScriptResult(
            output_id="snapshot-ref", actual=Budget(), publication=publication
        )

    async def late():
        pytest.fail("late callback must not run")

    controller, _, _ = setup(callbacks=[early, late])
    assert (await controller.run()).stop_reason == "premature_publication"
