from dataclasses import dataclass, field
from types import MappingProxyType
from collections.abc import Mapping
from typing import Any
import json
import hashlib

from openrat.core.errors import UserInputError


@dataclass(frozen=True)
class ExperimentSpec:
    """Declarative intent for an experiment.

    This object is immutable after construction and can be deterministically
    serialized to draft/final JSON forms used by planning.
    """

    goals: tuple[str, ...]
    metrics: Mapping[str, Any]
    tasks: Mapping[str, Mapping[str, Any]]
    dependencies: Mapping[str, tuple[str, ...]] = field(default_factory=dict)
    constraints: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "goals", tuple(self.goals))
        object.__setattr__(self, "metrics", MappingProxyType(dict(self.metrics)))

        normalized_tasks: dict[str, Mapping[str, Any]] = {}
        for task_id, cfg in dict(self.tasks).items():
            normalized_tasks[str(task_id)] = MappingProxyType(dict(cfg))
        object.__setattr__(self, "tasks", MappingProxyType(normalized_tasks))

        normalized_deps: dict[str, tuple[str, ...]] = {}
        for task_id, deps in dict(self.dependencies).items():
            normalized_deps[str(task_id)] = tuple(deps)
        object.__setattr__(self, "dependencies", MappingProxyType(normalized_deps))

        object.__setattr__(self, "constraints", MappingProxyType(dict(self.constraints)))

    @classmethod
    def from_final_json(cls, data: Mapping[str, Any]) -> "ExperimentSpec":
        goals = tuple(data.get("goals", ()))
        metrics = data.get("metrics", {})
        tasks = data.get("tasks", {})
        dependencies = data.get("dependencies", {})
        constraints = data.get("constraints", {})
        spec = cls(
            goals=goals,
            metrics=metrics,
            tasks=tasks,
            dependencies=dependencies,
            constraints=constraints,
        )
        spec.validate()
        return spec

    @classmethod
    def from_draft_json(cls, draft: Mapping[str, Any]) -> "ExperimentSpec":
        """Deterministic draft → final object transformation."""
        return cls.from_final_json(draft)

    def validate(self) -> None:
        if not self.goals:
            raise UserInputError("ExperimentSpec must define at least one goal")

        if not self.tasks:
            raise UserInputError("ExperimentSpec must define at least one task")

        for task_id, task in self.tasks.items():
            if "tool" not in task:
                raise UserInputError(f"Task {task_id} missing required 'tool' field")

        for task_id, deps in self.dependencies.items():
            if task_id not in self.tasks:
                raise UserInputError(f"Unknown task in dependencies: {task_id}")
            for dep in deps:
                if dep not in self.tasks:
                    raise UserInputError(f"Task {task_id} depends on unknown task {dep}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "goals": list(self.goals),
            "metrics": dict(self.metrics),
            "tasks": {task_id: dict(cfg) for task_id, cfg in self.tasks.items()},
            "dependencies": {task_id: list(deps) for task_id, deps in self.dependencies.items()},
            "constraints": dict(self.constraints),
        }

    def to_draft_json(self) -> dict[str, Any]:
        """Deterministic object → draft JSON transformation."""
        return self.to_dict()

    def stable_hash(self) -> str:
        payload = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(payload).hexdigest()

    def to_dag_spec(self) -> dict[str, Any]:
        """Pure transformation: ExperimentSpec → DAG inputs."""
        self.validate()

        from openrat.tasks.dag.task import Task

        dag_tasks = {}
        for task_id, cfg in self.tasks.items():
            dag_tasks[task_id] = Task(
                id=task_id,
                tool_name=cfg["tool"],
                input=cfg.get("input"),
                retries=int(cfg.get("retries", 0)),
            )

        return {
            "tasks": dag_tasks,
            "edges": {task_id: tuple(deps) for task_id, deps in self.dependencies.items()},
        }