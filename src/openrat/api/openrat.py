from collections.abc import Iterable, Mapping
from typing import Any, TYPE_CHECKING

from openrat.core.artifact import Artifact
from openrat.core.governance.autonomy import AutonomyLevel
from openrat.core.experiment_spec import ExperimentSpec
from openrat.core.session.session import Session
from openrat.model.types import Message, ModelResponse
from openrat.core.protocols import ToolProtocol, ToolRegistryProtocol
from openrat.tasks.plan.plan import Plan

if TYPE_CHECKING:
    from .runner import OpenRatAgent


class Openrat:
    """Framework facade for experiment orchestration.

    Orchestrates the workflow:
    1. create_session() — define autonomy and governance
    2. build_plan() — construct execution plan from spec
    3. execute_plan() — execute with policy approval

    Also provides direct execution (app.run()) and LLM loops (app.chat())
    for convenience, though the framework workflow is recommended.
    """

    def __init__(self, config: Mapping[str, Any] | None = None):
        self._config = dict(config or {})
        self._agent: "OpenRatAgent | None" = None

    def _ensure_agent(self) -> "OpenRatAgent":
        if self._agent is None:
            from .runner import OpenRatAgent

            self._agent = OpenRatAgent(self._config)
        return self._agent

    @property
    def tool_registry(self) -> ToolRegistryProtocol | None:
        """Low-level tool registry (internal extension point).

        This property is provided for advanced use cases that register custom tools
        for the LLM loop. It is not part of the planned session/spec/plan/artifact
        workflow and should be considered internal — subject to change.

        For most use cases, use the framework workflow instead:
            plan = app.build_plan(spec, session)
            artifact = app.execute_plan(plan)
        """
        return getattr(self._ensure_agent(), "tool_registry", None)

    def run(
        self,
        path: str,
        timeout: int | None = None,
        isolate: bool = True,
        memory: str = "512m",
        cpus: str = "1.0",
    ) -> Mapping[str, Any]:
        """Direct compatibility path (non-planned execution)."""
        return self._ensure_agent().run(
            path,
            timeout=timeout,
            isolate=isolate,
            memory=memory,
            cpus=cpus,
        )

    def chat(self, messages: str | list[Message], max_turns: int = 10) -> ModelResponse:
        """Direct compatibility path to the low-level LLM agent loop."""
        return self._ensure_agent().chat(messages, max_turns=max_turns)

    def create_session(
        self,
        *,
        autonomy: AutonomyLevel,
        patch_policy: str,
        user_approvals: Iterable[str] | None = None,
    ) -> Session:
        return Session(
            autonomy=autonomy,
            patch_policy=patch_policy,
            user_approvals=set(user_approvals or set()),
        )

    def spec_from_final_json(self, data: Mapping[str, Any]) -> ExperimentSpec:
        return ExperimentSpec.from_final_json(data)

    def build_plan(
        self,
        spec: ExperimentSpec,
        session: Session,
        tool_capabilities: Mapping[str, str] | None = None,
    ) -> Plan:
        return Plan.build(spec, session, tool_capabilities=tool_capabilities)

    def execute_plan(self, plan: Plan, session: Session, tools: Mapping[str, ToolProtocol]) -> Artifact:
        plan.assert_executable()
        plan.dag.execute(tools=tools, session=session)
        return Artifact.from_dag_execution(
            dag=plan.dag,
            plan=plan,
            session=session,
            logs=(),
            metrics={},
            diagnostics={"governance": session.governance_report()},
            patches_applied=tuple(p.get("patch_id", "") for p in session.patches_applied),
        )
