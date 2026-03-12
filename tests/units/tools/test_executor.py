import sys
from pathlib import Path
import pytest

# ensure project root is importable
root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(root))

import openrat.tools.executor as executor_mod
from openrat.tools.base import ToolProposal
from openrat.errors import UserInputError, PolicyViolation, ExecutionError


class MockGovernance:
    def __init__(self, autonomy_level=0, allow=True):
        self.autonomy_level = autonomy_level
        self._allow = allow

    def authorize_execution(self, proposal):
        return self._allow


def test_valid_routing_returns_scheduled():
    gov = MockGovernance(autonomy_level=0, allow=True)
    exec_tool = executor_mod.Executor(gov)

    project_root = Path(__file__).resolve().parents[3]
    payload = {
        "executor_type": "docker",
        "command": ["python", "train.py"],
        "cwd": str((project_root / "sandbox")),
        "timeout": 10,
    }

    proposal = ToolProposal(tool_name="executor", payload=payload)
    result = exec_tool.execute(proposal)
    assert result["status"] == "scheduled"
    assert result["executor"] == "docker"


def test_unknown_executor_type_raises():
    gov = MockGovernance()
    exec_tool = executor_mod.Executor(gov)
    payload = {"executor_type": "nonexistent", "command": ["python", "x.py"]}
    proposal = ToolProposal(tool_name="executor", payload=payload)
    with pytest.raises(UserInputError):
        exec_tool.execute(proposal)


def test_command_not_whitelisted_raises():
    gov = MockGovernance()
    exec_tool = executor_mod.Executor(gov)
    project_root = Path(__file__).resolve().parents[3]
    payload = {
        "executor_type": "docker",
        "command": ["/bin/rm", "-rf", "/"],
        "cwd": str(project_root / "sandbox"),
    }
    proposal = ToolProposal(tool_name="executor", payload=payload)
    with pytest.raises(PolicyViolation):
        exec_tool.execute(proposal)


def test_cwd_outside_sandbox_raises():
    gov = MockGovernance()
    exec_tool = executor_mod.Executor(gov)
    project_root = Path(__file__).resolve().parents[3]
    payload = {
        "executor_type": "docker",
        "command": ["python", "train.py"],
        "cwd": str(project_root.parent),
    }
    proposal = ToolProposal(tool_name="executor", payload=payload)
    with pytest.raises(PolicyViolation):
        exec_tool.execute(proposal)


def test_governance_rejects_execution():
    gov = MockGovernance(autonomy_level=0, allow=False)
    exec_tool = executor_mod.Executor(gov)
    project_root = Path(__file__).resolve().parents[3]
    payload = {
        "executor_type": "docker",
        "command": ["python", "train.py"],
        "cwd": str(project_root / "sandbox"),
    }
    proposal = ToolProposal(tool_name="executor", payload=payload)
    with pytest.raises(PolicyViolation):
        exec_tool.execute(proposal)


def test_backend_exception_raises_execution_error(monkeypatch):
    gov = MockGovernance(autonomy_level=0, allow=True)
    exec_tool = executor_mod.Executor(gov)

    class BoomBackend:
        def execute(self, spec):
            raise RuntimeError("backend crashed")

    monkeypatch.setattr(executor_mod._REGISTRY, "get", lambda name: BoomBackend())

    project_root = Path(__file__).resolve().parents[3]
    payload = {
        "executor_type": "local",
        "command": ["python", "train.py"],
        "cwd": str(project_root / "sandbox"),
        "timeout": 10,
    }
    proposal = ToolProposal(tool_name="executor", payload=payload)
    with pytest.raises(ExecutionError, match="executor backend failed"):
        exec_tool.execute(proposal)
