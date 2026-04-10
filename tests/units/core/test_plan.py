import sys
from pathlib import Path

root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(root))

from openrat.core.experiment_spec import ExperimentSpec
from openrat.core.session.session import Session
from openrat.core.governance.autonomy import AutonomyLevel
from openrat._tasks.plan.plan import Plan
from openrat._tasks.dag.task import TaskState


def test_plan_is_descriptive_and_policy_checked_only():
    spec = ExperimentSpec.from_final_json(
        {
            "goals": ["reach target metric"],
            "metrics": {"score": {"target": 1.0}},
            "tasks": {
                "observe": {"tool": "observe_tool", "capability": "observe"},
                "modify": {"tool": "modify_tool", "capability": "params.modify"},
            },
            "dependencies": {"modify": ["observe"]},
            "constraints": {},
        }
    )
    session = Session(
        autonomy=AutonomyLevel.OBSERVE,
        patch_policy="interactive",
        user_approvals={"observe"},
    )

    plan = Plan.build(spec, session)

    assert plan.requires_approval is True
    assert len(plan.actions) == 2
    blocked = [a for a in plan.actions if not a.authorized]
    assert len(blocked) == 1
    assert blocked[0].task_id == "modify"

    # Planning should not execute anything
    assert all(record.state == TaskState.PENDING for record in plan.dag.state.values())
