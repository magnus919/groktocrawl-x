"""Finite local-script controller; no provider adapter, persistence or real verifier."""

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Annotated, Literal

from pydantic import Field

from .execution import Budget, ExecutionLedger, ExecutionState
from .knowledge import Digest, Identity, Record
from .publication import (
    FixturePublication,
    FixtureResearch,
    validate_fixture_publication,
)
from .verification import FixtureVerifier

Seconds = Annotated[float, Field(gt=0, le=3600, allow_inf_nan=False)]


class ControllerLimits(Record):
    overall_seconds: Seconds
    operation_seconds: Seconds
    cleanup_seconds: Annotated[float, Field(gt=0, le=1, allow_inf_nan=False)] = 0.05


class ScriptResult(Record):
    output_id: Identity
    actual: Budget
    publication: FixturePublication | None = None


class OperationSpec(Record):
    operation_id: Identity
    input_digest: Digest
    output_id: Identity
    reservation: Budget


@dataclass(frozen=True)
class ScriptStep:
    spec: OperationSpec
    execute: Callable[[], Awaitable[ScriptResult]]


class ControllerResult(Record):
    execution_outcome: Literal["completed", "failed", "cancelled"]
    answer_coverage: Literal["complete", "partial", "insufficient"] | None
    stop_reason: str
    accounting: ExecutionState
    publication: FixturePublication | None
    cleanup_incomplete: bool


class _StoppedError(Exception):
    def __init__(self, reason: str) -> None:
        self.reason = reason


class ScriptedController:
    """One event-loop owner; no retry, parallel dispatch or crash recovery."""

    def __init__(
        self,
        *,
        run_id: str,
        steps: tuple[ScriptStep, ...],
        budget: Budget,
        limits: ControllerLimits,
        research: FixtureResearch,
        artifact_set_id: str,
        renderer_version: str,
        auditor: FixtureVerifier,
    ) -> None:
        if not 1 <= len(steps) <= 100:
            raise ValueError("script must contain between one and 100 operations")
        self._steps = tuple(
            ScriptStep(OperationSpec.model_validate(step.spec), step.execute)
            for step in steps
        )
        if len({step.spec.operation_id for step in self._steps}) != len(self._steps):
            raise ValueError("script operation IDs must be unique")
        self._research = FixtureResearch.model_validate(research)
        self._limits = ControllerLimits.model_validate(limits)
        self._ledger = ExecutionLedger(
            run_id=run_id,
            policy_version=research.verifications.policy_version,
            limit=budget,
            max_operations=len(steps),
        )
        self._artifact_set_id = artifact_set_id
        self._renderer_version = renderer_version
        self._auditor = FixtureVerifier.model_validate(auditor)
        self._cancel = asyncio.Event()
        self._running = False
        self._result: ControllerResult | None = None
        self._pending: set[asyncio.Task[ScriptResult]] = set()

    @property
    def result(self) -> ControllerResult | None:
        return self._result

    def cancel(self) -> None:
        if self._result is None:
            self._cancel.set()

    def _consume_late(self, task: asyncio.Task[ScriptResult]) -> None:
        self._pending.discard(task)
        if not task.cancelled():
            task.exception()  # Consume late failures; never apply their result.

    async def _invoke(self, step: ScriptStep, timeout: float) -> ScriptResult:
        # A wrapper also captures synchronous callback exceptions as task failures.
        async def invoke() -> ScriptResult:
            return await step.execute()

        task = asyncio.create_task(invoke())
        cancelled = asyncio.create_task(self._cancel.wait())
        try:
            done, _ = await asyncio.wait(
                {task, cancelled}, timeout=timeout, return_when=asyncio.FIRST_COMPLETED
            )
            if self._cancel.is_set():
                raise _StoppedError("cancelled")
            if task not in done:
                raise _StoppedError("deadline_exceeded")
            return ScriptResult.model_validate(task.result())
        finally:
            cancelled.cancel()
            if not task.done():
                task.cancel()
                try:
                    await asyncio.wait({task}, timeout=self._limits.cleanup_seconds)
                finally:
                    if not task.done():
                        self._pending.add(task)
                    task.add_done_callback(self._consume_late)
            elif not task.cancelled():
                task.exception()

    def _stop(self, reason: str) -> ControllerResult:
        outcome: Literal["failed", "cancelled"] = (
            "cancelled" if reason == "cancelled" else "failed"
        )
        if outcome == "cancelled":
            state = self._ledger.cancel(expected_revision=self._ledger.state.revision)
        else:
            state = self._ledger.finish(
                outcome="failed", expected_revision=self._ledger.state.revision
            )
        self._result = ControllerResult(
            execution_outcome=outcome,
            answer_coverage=None,
            stop_reason=reason,
            accounting=state,
            publication=None,
            cleanup_incomplete=bool(self._pending),
        )
        return self._result

    async def run(self) -> ControllerResult:
        if self._result is not None:
            return self._result
        if self._running:
            raise RuntimeError("controller already running")
        self._running = True
        loop = asyncio.get_running_loop()
        deadline = loop.time() + self._limits.overall_seconds
        candidate: FixturePublication | None = None
        try:
            for index, step in enumerate(self._steps):
                if self._cancel.is_set():
                    raise _StoppedError("cancelled")
                remaining = deadline - loop.time()
                if remaining <= 0:
                    raise _StoppedError("deadline_exceeded")
                try:
                    self._ledger.reserve(
                        operation_id=step.spec.operation_id,
                        input_digest=step.spec.input_digest,
                        budget=step.spec.reservation,
                        expected_revision=self._ledger.state.revision,
                    )
                except ValueError:
                    raise _StoppedError("budget_exhausted") from None
                result = await self._invoke(
                    step, min(remaining, self._limits.operation_seconds)
                )
                if self._cancel.is_set():
                    raise _StoppedError("cancelled")
                if loop.time() >= deadline:
                    raise _StoppedError("deadline_exceeded")
                if result.output_id != step.spec.output_id:
                    raise _StoppedError("output_identity_mismatch")
                if result.publication is not None and index != len(self._steps) - 1:
                    raise _StoppedError("premature_publication")
                self._ledger.complete(
                    operation_id=step.spec.operation_id,
                    input_digest=step.spec.input_digest,
                    output_id=result.output_id,
                    actual=result.actual,
                    expected_revision=self._ledger.state.revision,
                )
                candidate = result.publication
            try:
                publication = validate_fixture_publication(
                    candidate,
                    research=self._research,
                    artifact_set_id=self._artifact_set_id,
                    renderer_version=self._renderer_version,
                    auditor=self._auditor,
                )
            except ValueError:
                raise _StoppedError("publication_rejected") from None
            if self._cancel.is_set():
                raise _StoppedError("cancelled")
            if loop.time() >= deadline:
                raise _StoppedError("deadline_exceeded")
            state = self._ledger.finish(
                outcome="completed", expected_revision=self._ledger.state.revision
            )
            coverage = self._research.coverage()
            reason = (
                "coverage_satisfied"
                if coverage == "complete"
                else "unresolved_conflict"
                if self._research.conflicts
                else "insufficient_evidence"
            )
            self._result = ControllerResult(
                execution_outcome="completed",
                answer_coverage=coverage,
                stop_reason=reason,
                accounting=state,
                publication=publication,
                cleanup_incomplete=False,
            )
            return self._result
        except _StoppedError as stopped:
            return self._stop(stopped.reason)
        except asyncio.CancelledError:
            self._cancel.set()
            self._stop("cancelled")
            raise
        except Exception:
            return self._stop("operation_failed")
        finally:
            self._running = False
