import sys
from pathlib import Path

import pytest

root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root))

from openrat import Openrat, BaseTool
from openrat.core.governance.autonomy import AutonomyLevel
from openrat.core.errors import PolicyViolation
from openrat.tasks.dag.task import TaskState


class ObserveTool(BaseTool):
    capability = "observe"

    def run(self, payload, session):
        return {"observed": payload["name"]}


class ModifyTool(BaseTool):
    capability = "params.modify"

    def run(self, payload, session):
        return {"modified": payload.get("name")}


def test_spec_plan_dag_artifact_flow_end_to_end():
    app = Openrat({"executor": "docker"})

    spec = app.spec_from_final_json(
        {
            "goals": ["collect observations"],
            "metrics": {"count": {"target": 2}},
            "tasks": {
                "t1": {"tool": "observe", "input": {"name": "alpha"}, "capability": "observe"},
                "t2": {"tool": "observe", "input": {"name": "beta"}, "capability": "observe"},
            },
            "dependencies": {"t2": ["t1"]},
            "constraints": {"patch_policy": "interactive"},
        }
    )

    session = app.create_session(
        autonomy=AutonomyLevel.OBSERVE,
        patch_policy="interactive",
        user_approvals={"observe"},
    )

    plan = app.build_plan(spec, session)
    assert plan.requires_approval is False

    artifact = app.execute_plan(
        plan,
        session,
        tools={"observe": ObserveTool()},
    )

    assert plan.dag.state["t1"].state == TaskState.SUCCESS
    assert plan.dag.state["t2"].state == TaskState.SUCCESS

    summary = artifact.summarize()
    assert summary["status"] == "success"
    assert summary["patches_applied"] == 0
    assert artifact.to_dict()["observations"]["t1"]["observed"] == "alpha"
    assert "governance" in artifact.to_dict()["diagnostics"]
    assert isinstance(artifact.logs, tuple)


def test_openrat_execute_plan_requires_approved_plan():
    app = Openrat({"executor": "docker"})

    spec = app.spec_from_final_json(
        {
            "goals": ["collect observations"],
            "metrics": {"count": {"target": 1}},
            "tasks": {
                "t1": {"tool": "observe", "input": {"name": "alpha"}, "capability": "observe"},
                "t2": {"tool": "modify", "input": {"name": "beta"}, "capability": "params.modify"},
            },
            "dependencies": {"t2": ["t1"]},
            "constraints": {"patch_policy": "interactive"},
        }
    )

    session = app.create_session(
        autonomy=AutonomyLevel.OBSERVE,
        patch_policy="interactive",
        user_approvals={"observe"},
    )

    plan = app.build_plan(spec, session)
    assert plan.requires_approval is True

    with pytest.raises(PolicyViolation, match="requires approval"):
        app.execute_plan(
            plan,
            session,
            tools={"observe": ObserveTool(), "modify": ModifyTool()},
        )
