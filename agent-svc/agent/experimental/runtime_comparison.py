"""Equivalent imperative and graph-shaped fixture runtimes.

The adapters own scheduling only. Operation callbacks, budgets, receipts and
terminal rules are shared so a runtime comparison cannot quietly compare two
different research policies. This is a deterministic conformance harness, not
the adopted production runtime or recovery implementation.
"""

import asyncio
import hashlib
import json
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass
from typing import Literal, Protocol

from .controller import OperationSpec, ScriptResult
from .execution import Budget, ExecutionLedger, ExecutionState

RuntimeName = Literal["imperative", "graph-candidate"]
EventKind = Literal[
    "reserved",
    "started",
    "completed",
    "failed",
    "cancelled",
    "terminal",
]


@dataclass(frozen=True)
class RuntimeNode:
    spec: OperationSpec
    execute: Callable[[], Awaitable[ScriptResult]]
    depends_on: tuple[str, ...] = ()


@dataclass(frozen=True)
class RuntimePlan:
    run_id: str
    policy_version: str
    nodes: tuple[RuntimeNode, ...]
    budget: Budget
    max_operations: int

    def ordered(self) -> tuple[RuntimeNode, ...]:
        identities = {node.spec.operation_id for node in self.nodes}
        if len(identities) != len(self.nodes):
            raise ValueError("runtime operation IDs must be unique")
        for node in self.nodes:
            if set(node.depends_on) - identities:
                raise ValueError("runtime dependency is unknown")
            if node.spec.operation_id in node.depends_on:
                raise ValueError("runtime operation cannot depend on itself")
        pending = {node.spec.operation_id: node for node in self.nodes}
        result: list[RuntimeNode] = []
        while pending:
            ready = sorted(
                (
                    node
                    for node in pending.values()
                    if all(dep not in pending for dep in node.depends_on)
                ),
                key=lambda node: node.spec.operation_id,
            )
            if not ready:
                raise ValueError("runtime dependency graph contains a cycle")
            for node in ready:
                result.append(node)
                del pending[node.spec.operation_id]
        return tuple(result)


@dataclass(frozen=True)
class RuntimeEvent:
    sequence: int
    kind: EventKind
    operation_id: str | None
    revision: int


@dataclass(frozen=True)
class RuntimeOutcome:
    runtime: RuntimeName
    accounting: ExecutionState
    outputs: tuple[tuple[str, str], ...]
    events: tuple[RuntimeEvent, ...]

    @property
    def fingerprint(self) -> str:
        payload = {
            "accounting": self.accounting.model_dump(mode="json"),
            "outputs": self.outputs,
        }
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()


class RuntimeAdapter(Protocol):
    async def run(
        self, plan: RuntimePlan, *, cancel: asyncio.Event | None = None
    ) -> RuntimeOutcome: ...


class _Runner:
    def __init__(self, plan: RuntimePlan, runtime: RuntimeName) -> None:
        self.plan = plan
        self.runtime = runtime
        self.ledger = ExecutionLedger(
            run_id=plan.run_id,
            policy_version=plan.policy_version,
            limit=plan.budget,
            max_operations=plan.max_operations,
        )
        self.events: list[RuntimeEvent] = []
        self.outputs: dict[str, str] = {}

    def event(self, kind: EventKind, operation_id: str | None = None) -> None:
        self.events.append(
            RuntimeEvent(
                len(self.events), kind, operation_id, self.ledger.state.revision
            )
        )

    def outcome(self) -> RuntimeOutcome:
        return RuntimeOutcome(
            self.runtime,
            self.ledger.state,
            tuple(sorted(self.outputs.items())),
            tuple(self.events),
        )

    def reserve(self, node: RuntimeNode) -> None:
        before = self.ledger.state.revision
        self.ledger.reserve(
            operation_id=node.spec.operation_id,
            input_digest=node.spec.input_digest,
            budget=node.spec.reservation,
            expected_revision=before,
        )
        if self.ledger.state.revision != before:
            self.event("reserved", node.spec.operation_id)

    async def invoke(
        self, node: RuntimeNode, cancel: asyncio.Event | None
    ) -> tuple[RuntimeNode, ScriptResult | None, BaseException | None]:
        self.event("started", node.spec.operation_id)
        async def execute() -> ScriptResult:
            return await node.execute()

        task: asyncio.Task[ScriptResult] = asyncio.create_task(execute())
        cancel_task = asyncio.create_task(cancel.wait()) if cancel is not None else None
        try:
            if cancel_task is None:
                return node, await task, None
            done, _ = await asyncio.wait(
                {task, cancel_task}, return_when=asyncio.FIRST_COMPLETED
            )
            if cancel_task in done and cancel is not None and cancel.is_set():
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
                return node, None, asyncio.CancelledError()
            return node, task.result(), None
        except BaseException as error:  # callback failures are trace data
            return node, None, error
        finally:
            if cancel_task is not None:
                cancel_task.cancel()
                await asyncio.gather(cancel_task, return_exceptions=True)

    def complete(self, node: RuntimeNode, result: ScriptResult) -> None:
        before = self.ledger.state.revision
        self.ledger.complete(
            operation_id=node.spec.operation_id,
            input_digest=node.spec.input_digest,
            output_id=result.output_id,
            actual=result.actual,
            expected_revision=before,
        )
        self.outputs[node.spec.operation_id] = result.output_id
        self.event("completed", node.spec.operation_id)

    def fail(self, outcome: Literal["failed", "cancelled"]) -> None:
        before = self.ledger.state.revision
        if outcome == "cancelled":
            self.ledger.cancel(expected_revision=before)
            self.event("cancelled")
        else:
            self.ledger.finish(outcome="failed", expected_revision=before)
            self.event("failed")
        self.event("terminal")

    def finish(self) -> None:
        before = self.ledger.state.revision
        self.ledger.finish(outcome="completed", expected_revision=before)
        self.event("terminal")


class ImperativeRuntime:
    async def run(
        self, plan: RuntimePlan, *, cancel: asyncio.Event | None = None
    ) -> RuntimeOutcome:
        ordered = plan.ordered()
        runner = _Runner(plan, "imperative")
        try:
            for node in ordered:
                if cancel is not None and cancel.is_set():
                    runner.fail("cancelled")
                    return runner.outcome()
                runner.reserve(node)
                current, result, error = await runner.invoke(node, cancel)
                if error is not None:
                    runner.fail("cancelled" if isinstance(error, asyncio.CancelledError) else "failed")
                    return runner.outcome()
                assert result is not None
                runner.complete(current, result)
            runner.finish()
        except BaseException:
            if runner.ledger.state.state == "running":
                runner.fail("failed")
            return runner.outcome()
        return runner.outcome()


class GraphCandidateRuntime:
    """Small explicit graph scheduler used until a framework is authorized."""

    async def run(
        self, plan: RuntimePlan, *, cancel: asyncio.Event | None = None
    ) -> RuntimeOutcome:
        runner = _Runner(plan, "graph-candidate")
        nodes = {node.spec.operation_id: node for node in plan.nodes}
        remaining = set(nodes)
        running: dict[
            asyncio.Task[tuple[RuntimeNode, ScriptResult | None, BaseException | None]],
            RuntimeNode,
        ] = {}
        try:
            while remaining or running:
                if cancel is not None and cancel.is_set():
                    for task in running:
                        task.cancel()
                    await asyncio.gather(*running, return_exceptions=True)
                    runner.fail("cancelled")
                    return runner.outcome()
                ready = sorted(
                    (
                        node
                        for identity, node in nodes.items()
                        if identity in remaining
                        and all(dep in runner.outputs for dep in node.depends_on)
                    ),
                    key=lambda node: node.spec.operation_id,
                )
                for node in ready:
                    runner.reserve(node)
                    remaining.remove(node.spec.operation_id)
                    task = asyncio.create_task(runner.invoke(node, cancel))
                    running[task] = node
                if not running:
                    raise ValueError("graph made no progress")
                done, _ = await asyncio.wait(
                    running, return_when=asyncio.FIRST_COMPLETED
                )
                results = []
                for task in done:
                    del running[task]
                    results.append(await task)
                for node, result, error in sorted(
                    results, key=lambda item: item[0].spec.operation_id
                ):
                    if error is not None:
                        for task in running:
                            task.cancel()
                        await asyncio.gather(*running, return_exceptions=True)
                        runner.fail(
                            "cancelled"
                            if isinstance(error, asyncio.CancelledError)
                            else "failed"
                        )
                        return runner.outcome()
                    assert result is not None
                    runner.complete(node, result)
            runner.finish()
        except BaseException:
            if runner.ledger.state.state == "running":
                runner.fail("failed")
            return runner.outcome()
        return runner.outcome()


def compare_outcomes(
    outcomes: Iterable[RuntimeOutcome],
) -> tuple[str, ...]:
    """Return explicit conformance failures; empty means equivalent outcomes."""
    values = tuple(outcomes)
    if not values:
        raise ValueError("at least one runtime outcome is required")
    reference = values[0]
    failures = []
    for candidate in values[1:]:
        if candidate.accounting != reference.accounting:
            failures.append(f"{candidate.runtime}: accounting differs")
        if candidate.outputs != reference.outputs:
            failures.append(f"{candidate.runtime}: outputs differ")
    return tuple(failures)
