import sys
from pathlib import Path

root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(root))

from openrat._tasks.dag.dag import DAG
from openrat._tasks.dag.task import Task, TaskState
from openrat.core.session.session import Session
from openrat.core.governance.autonomy import AutonomyLevel
from openrat.tools.base import BaseTool


class ObserveTool(BaseTool):
    capability = "observe"

    def run(self, payload, session):
        return {"value": payload["value"]}


class ModifyTool(BaseTool):
    capability = "params.modify"

    def run(self, payload, session):
        return {"updated": True, "value": payload["value"]}


def test_dag_executes_in_dependency_order_when_authorized():
    tasks = {
        "a": Task(id="a", tool_name="observe", input={"value": 1}, retries=0),
        "b": Task(id="b", tool_name="modify", input={"value": 2}, retries=0),
    }
    edges = {"b": ["a"]}
    dag = DAG(tasks, edges)

    session = Session(
        autonomy=AutonomyLevel.PARAMS_ONLY,
        patch_policy="interactive",
        user_approvals={"observe", "params.modify"},
    )

    tools = {
        "observe": ObserveTool(),
        "modify": ModifyTool(),
    }

    state = dag.execute(tools, session)
    assert state["a"].state == TaskState.SUCCESS
    assert state["b"].state == TaskState.SUCCESS
    assert state["b"].outputs["updated"] is True


def test_dag_skips_unauthorized_task_without_policy_ownership():
    tasks = {
        "a": Task(id="a", tool_name="modify", input={"value": 1}, retries=0),
    }
    dag = DAG(tasks, edges={})

    session = Session(
        autonomy=AutonomyLevel.OBSERVE,
        patch_policy="interactive",
        user_approvals={"observe"},
    )

    tools = {"modify": ModifyTool()}
    state = dag.execute(tools, session)

    assert state["a"].state == TaskState.SKIPPED
    assert "autonomy" in (state["a"].error or "") or "requires explicit approval" in (state["a"].error or "")
