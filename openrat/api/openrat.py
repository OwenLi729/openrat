from typing import Any, Mapping, Optional, TYPE_CHECKING

from openrat.core.artifact import Artifact
from openrat.core.instructions import ExperimentSpec
from openrat.core.session.session import Session
from openrat.tasks.plan.plan import Plan

if TYPE_CHECKING:
    from .runner import OpenRatAgent


class Openrat:
    """Recommended public facade for Openrat framework workflows.

    Core workflow ownership lives here:
    1) create a ``Session``,
    2) construct an ``ExperimentSpec``,
    3) build a ``Plan``,
    4) execute plan -> ``Artifact``.

    ``run()`` and ``chat()`` are compatibility forwards to ``OpenRatAgent`` and
    are direct (non-planned) execution paths.
    """

    def __init__(self, config: Optional[dict] = None):
        self._config = dict(config or {})
        self._agent: "OpenRatAgent | None" = None

    def _ensure_agent(self) -> "OpenRatAgent":
        if self._agent is None:
            from .runner import OpenRatAgent

            self._agent = OpenRatAgent(self._config)
        return self._agent

    @property
    def tool_registry(self):
        """Compatibility access to the low-level tool registry.

        This property is provided for advanced/legacy flows that register tools
        for the direct LLM loop path. It is not part of the planned
        session/spec/plan/artifact workflow.
        """
        return getattr(self._ensure_agent(), "tool_registry", None)

    def run(
        self,
        path: str,
        timeout: Optional[int] = None,
        isolate: bool = True,
        memory: str = "512m",
        cpus: str = "1.0",
    ):
        """Direct compatibility path (non-planned execution)."""
        return self._ensure_agent().run(
            path,
            timeout=timeout,
            isolate=isolate,
            memory=memory,
            cpus=cpus,
        )

    def chat(self, messages, max_turns: int = 10):
        """Direct compatibility path to the low-level LLM agent loop."""
        return self._ensure_agent().chat(messages, max_turns=max_turns)

    def create_session(self, *, autonomy, patch_policy: str, user_approvals=None) -> Session:
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

    def execute_plan(self, plan: Plan, session: Session, tools: Mapping[str, Any]) -> Artifact:
        plan.assert_executable()
        plan.dag.execute(tools=tools, session=session)
        return Artifact.from_dag_execution(
            dag=plan.dag,
            plan=plan,
            session=session,
            logs=(),
            metrics={},
            diagnostics={},
            patches_applied=(),
        )
