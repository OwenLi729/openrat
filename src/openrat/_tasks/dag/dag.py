from datetime import datetime, timezone
from collections.abc import Iterable, Mapping
from typing import Any

from openrat.core.errors import UserInputError, InternalError, PolicyViolation
from openrat.core._protocols import SessionProtocol, ToolProtocol
from openrat._tasks.dag.task import Task, TaskExecution, TaskState


class DAG:
    def __init__(
        self,
        tasks: Mapping[str, Task],
        edges: Mapping[str, Iterable[str]],
    ):
        """Execution graph for tasks and dependencies."""
        self.tasks = dict(tasks)
        self.edges = {k: tuple(v) for k, v in edges.items()}
        self.reverse_edges = self._build_reverse_edges()
        self.state = {
            task_id: TaskExecution(task_id)
            for task_id in self.tasks
        }

        self._validate()

    def _validate(self) -> None:
        for task_id, deps in self.edges.items():
            if task_id not in self.tasks:
                raise UserInputError(f"Unknown task in DAG edges: {task_id}")
            for dep in deps:
                if dep not in self.tasks:
                    raise UserInputError(f"Task {task_id} depends on unknown task {dep}")
        self._assert_acyclic()

    def _assert_acyclic(self) -> None:
        visited = set()
        stack = set()

        def visit(node: str):
            if node in stack:
                raise UserInputError("DAG contains a cycle")
            if node in visited:
                return
            stack.add(node)
            for dep in self.edges.get(node, ()): 
                visit(dep)
            stack.remove(node)
            visited.add(node)

        for task_id in self.tasks:
            visit(task_id)

    def _build_reverse_edges(self) -> dict[str, set[str]]:
        reverse = {task_id: set() for task_id in self.tasks}
        for task_id, deps in self.edges.items():
            for dep in deps:
                reverse[dep].add(task_id)
        return reverse

    def _is_ready(self, task_id: str) -> bool:
        deps = self.edges.get(task_id, ())
        return all(self.state[dep].state == TaskState.SUCCESS for dep in deps)

    def _transition(self, task_id: str, new_state: TaskState, error: str | None = None) -> None:
        record = self.state[task_id]
        old_state = record.state

        valid = {
            TaskState.PENDING: {TaskState.READY},
            TaskState.READY: {TaskState.RUNNING, TaskState.SKIPPED},
            TaskState.RUNNING: {TaskState.SUCCESS, TaskState.FAILED, TaskState.SKIPPED},
            TaskState.FAILED: {TaskState.READY, TaskState.SKIPPED},
            TaskState.SUCCESS: set(),
            TaskState.SKIPPED: set(),
        }

        if new_state not in valid.get(old_state, set()):
            raise InternalError(f"Invalid transition {old_state} -> {new_state}")

        record.state = new_state

        if new_state == TaskState.RUNNING:
            record.attempts += 1
            record.started_at = datetime.now(timezone.utc)

        if new_state in (TaskState.SUCCESS, TaskState.FAILED, TaskState.SKIPPED):
            record.finished_at = datetime.now(timezone.utc)
            record.error = error

    def execute(self, tools: Mapping[str, ToolProtocol], session: SessionProtocol) -> dict[str, TaskExecution]:
        """Execute authorized tasks in dependency order.

        Policy decisions are delegated exclusively to the provided session.
        """
        while True:
            progress = False

            for task_id, task in self.tasks.items():
                record = self.state[task_id]

                if record.state == TaskState.PENDING and self._is_ready(task_id):
                    self._transition(task_id, TaskState.READY)
                    progress = True

                if record.state != TaskState.READY:
                    continue

                tool = tools.get(task.tool_name)
                if tool is None:
                    self._transition(task_id, TaskState.SKIPPED, error=f"Tool '{task.tool_name}' not found")
                    progress = True
                    continue

                capability = getattr(tool, "capability", "observe")

                try:
                    allowed = session.authorize(
                        capability,
                        dry_run=False,
                        action="dag.execute.task",
                        metadata={"task_id": task_id, "tool": task.tool_name},
                    )
                except PolicyViolation as exc:
                    self._transition(task_id, TaskState.SKIPPED, error=str(exc))
                    progress = True
                    continue

                if not allowed:
                    self._transition(task_id, TaskState.SKIPPED, error="Not authorized by session policy")
                    progress = True
                    continue

                try:
                    self._transition(task_id, TaskState.RUNNING)
                    output = tool.run(task.input, session)
                    record.outputs = output or {}
                    self._transition(task_id, TaskState.SUCCESS)
                except Exception as exc:
                    if record.attempts <= task.retries:
                        self._transition(task_id, TaskState.FAILED, error=str(exc))
                        self._transition(task_id, TaskState.READY)
                    else:
                        self._transition(task_id, TaskState.FAILED, error=str(exc))

                progress = True

            if not progress:
                break

        return self.state