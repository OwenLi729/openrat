from dataclasses import dataclass, field
from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Any
from types import MappingProxyType
from datetime import datetime, timezone
from uuid import UUID, uuid4

if TYPE_CHECKING:
    from openrat.core.session.session import Session
    from openrat.tasks.dag.dag import DAG
    from openrat.tasks.plan.plan import Plan


@dataclass(frozen=True)
class Artifact:
    """Immutable result of experiment execution.
    
    Contains observations, evaluations, logs, and metadata from a completed run.
    """
    id: UUID
    created_at: datetime

    observations: Mapping[str, Any]
    evaluations: Mapping[str, Any]
    diagnostics: Mapping[str, Any]

    logs: Sequence[str]
    patches_applied: Sequence[str]

    metadata: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        *,
        observations: Mapping[str, Any],
        evaluations: Mapping[str, Any],
        diagnostics: Mapping[str, Any],
        logs: Sequence[str],
        patches_applied: Sequence[str],
        metadata: Mapping[str, Any] | None = None,
    ) -> "Artifact":
        """Create an immutable execution artifact."""
        return cls(
            id=uuid4(),
            created_at=datetime.now(timezone.utc),
            observations=MappingProxyType(dict(observations)),
            evaluations=MappingProxyType(dict(evaluations)),
            diagnostics=MappingProxyType(dict(diagnostics)),
            logs=tuple(logs),
            patches_applied=tuple(patches_applied),
            metadata=MappingProxyType(dict(metadata or {})),
        )

    @classmethod
    def from_dag_execution(
        cls,
        *,
        dag: "DAG",
        plan: "Plan",
        session: "Session",
        logs: Sequence[str] = (),
        metrics: Mapping[str, Any] | None = None,
        diagnostics: Mapping[str, Any] | None = None,
        patches_applied: Sequence[str] = (),
    ) -> "Artifact":
        observations = {
            task_id: dict(record.outputs)
            for task_id, record in dag.state.items()
            if record.outputs
        }
        failed = [
            task_id
            for task_id, record in dag.state.items()
            if getattr(record.state, "value", str(record.state)) == "failed"
        ]

        return cls.create(
            observations=observations,
            evaluations={
                "status": "failed" if failed else "success",
                "metrics": dict(metrics or {}),
            },
            diagnostics=dict(diagnostics or {}),
            logs=tuple(logs),
            patches_applied=tuple(patches_applied),
            metadata={
                "plan_id": str(plan.id),
                "session_id": str(session.id),
                "failed_tasks": failed,
            },
        )
    
    def summarize(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "status": self.evaluations.get("status"),
            "metrics": self.evaluations.get("metrics", {}),
            "patches_applied": len(self.patches_applied),
        }

    def has_failures(self) -> bool:
        return bool(self.diagnostics)

    #Minimal serialization:

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "created_at": self.created_at.isoformat(),
            "observations": dict(self.observations),
            "evaluations": dict(self.evaluations),
            "diagnostics": dict(self.diagnostics),
            "logs": list(self.logs),
            "patches_applied": list(self.patches_applied),
            "metadata": dict(self.metadata),
        }