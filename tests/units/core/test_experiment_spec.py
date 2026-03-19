import sys
from pathlib import Path
import pytest

root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(root))

from openrat.core.instructions import ExperimentSpec
from openrat.errors import UserInputError


def _valid_spec_payload():
    return {
        "goals": ["improve accuracy"],
        "metrics": {"accuracy": {"target": 0.9}},
        "tasks": {
            "observe_data": {"tool": "observe_tool", "input": {"path": "data.csv"}},
            "train": {"tool": "train_tool", "input": {"epochs": 2}, "retries": 1},
        },
        "dependencies": {"train": ["observe_data"]},
        "constraints": {"autonomy": "observe"},
    }


def test_experiment_spec_deterministic_and_dag_transform():
    payload = _valid_spec_payload()
    spec1 = ExperimentSpec.from_final_json(payload)
    spec2 = ExperimentSpec.from_draft_json(spec1.to_draft_json())

    assert spec1.stable_hash() == spec2.stable_hash()

    dag_spec = spec1.to_dag_spec()
    assert set(dag_spec["tasks"].keys()) == {"observe_data", "train"}
    assert dag_spec["tasks"]["train"].tool_name == "train_tool"
    assert dag_spec["edges"]["train"] == ("observe_data",)


def test_experiment_spec_requires_goals():
    payload = _valid_spec_payload()
    payload["goals"] = []
    with pytest.raises(UserInputError, match="at least one goal"):
        ExperimentSpec.from_final_json(payload)


def test_experiment_spec_requires_tasks():
    payload = _valid_spec_payload()
    payload["tasks"] = {}
    with pytest.raises(UserInputError, match="at least one task"):
        ExperimentSpec.from_final_json(payload)


def test_experiment_spec_requires_tool_per_task():
    payload = _valid_spec_payload()
    payload["tasks"]["observe_data"] = {"input": {"path": "x"}}
    with pytest.raises(UserInputError, match="missing required 'tool' field"):
        ExperimentSpec.from_final_json(payload)


def test_experiment_spec_dependency_validation():
    payload = _valid_spec_payload()
    payload["dependencies"] = {"train": ["unknown_task"]}
    with pytest.raises(UserInputError, match="depends on unknown task"):
        ExperimentSpec.from_final_json(payload)
