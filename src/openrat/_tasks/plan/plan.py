from dataclasses import dataclass
from collections.abc import Iterable, Mapping
from typing import Any
from uuid import UUID, uuid4

from openrat.core.experiment_spec import ExperimentSpec
from openrat.core.session.session import Session
from openrat.core.errors import PolicyViolation
from openrat.tasks.dag.dag import DAG


@dataclass(frozen=True)
class ProposedAction:
    task_id: str
    tool_name: str
    capability: str
    description: str
    authorized: bool
    reason: str | None = None


@dataclass(frozen=True)
class Plan:
    id: UUID
    spec_hash: str
    dag: DAG
    actions: tuple[ProposedAction, ...]
    requires_approval: bool

    @classmethod
    def build(
        cls,
        spec: ExperimentSpec,
        session: Session,
        tool_capabilities: Mapping[str, str] | None = None,
    ) -> "Plan":
        """Descriptive planning only: no execution occurs here."""
        dag_spec = spec.to_dag_spec()
        dag = DAG(tasks=dag_spec["tasks"], edges=dag_spec["edges"])

        capability_by_tool = dict(tool_capabilities or {})

        actions: list[ProposedAction] = []
        for task_id in sorted(spec.tasks.keys()):
            cfg = spec.tasks[task_id]
            tool_name = str(cfg["tool"])
            capability = str(cfg.get("capability") or capability_by_tool.get(tool_name) or "observe")

            authorized, reason = session.check_capability(capability)

            actions.append(
                ProposedAction(
                    task_id=task_id,
                    tool_name=tool_name,
                    capability=capability,
                    description=f"Run {tool_name} for task {task_id}",
                    authorized=authorized,
                    reason=reason,
                )
            )

        requires_approval = any(not action.authorized for action in actions)
        return cls(
            id=uuid4(),
            spec_hash=spec.stable_hash(),
            dag=dag,
            actions=tuple(actions),
            requires_approval=requires_approval,
        )

    def preview(self) -> Iterable[Mapping[str, Any]]:
        for action in self.actions:
            yield {
                "task_id": action.task_id,
                "tool": action.tool_name,
                "capability": action.capability,
                "authorized": action.authorized,
                "reason": action.reason,
            }

    def assert_executable(self) -> None:
        if self.requires_approval:
            raise PolicyViolation("Plan requires approval before execution")