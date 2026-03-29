import sys
from pathlib import Path

import pytest

root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(root))

from openrat.core.errors import UserInputError, PolicyViolation, ExecutionError
from openrat.core.governance.autonomy import AutonomyLevel
from openrat.core.session.session import Session
from openrat.tools.executor import ExecutorTool
from openrat.tools.registry import ToolRegistry


class _FakeBackend:
    def __init__(self, result=None, boom=False):
        self.result = result or {"status": "completed", "executor": "docker", "return_code": 0}
        self.boom = boom
        self.calls = []

    def execute(self, payload):
        self.calls.append(payload)
        if self.boom:
            raise RuntimeError("backend crashed")
        return self.result


def _observe_session() -> Session:
    return Session(
        autonomy=AutonomyLevel.OBSERVE,
        patch_policy="interactive",
        user_approvals={"observe"},
    )


def test_executor_tool_routes_to_backend(monkeypatch, tmp_path):
    backend = _FakeBackend(result={"status": "completed", "executor": "docker", "return_code": 0})
    monkeypatch.setattr("openrat.tools.executor.ExecutorRegistry.get", lambda name: backend)

    tool = ExecutorTool()
    session = _observe_session()
    payload = {
        "executor_type": "docker",
        "command": ["python", "-c", "print('ok')"],
        "cwd": str(tmp_path),
        "timeout": 30,
        "limits": {"memory": "128m", "cpus": "0.5"},
    }

    result = tool.run(payload, session)

    assert result["status"] == "completed"
    assert result["executor"] == "docker"
    assert backend.calls[0]["command"] == payload["command"]
    assert backend.calls[0]["limits"] == payload["limits"]


def test_executor_tool_unknown_executor_type_raises(monkeypatch, tmp_path):
    def _raise(name):
        raise KeyError(name)

    monkeypatch.setattr("openrat.tools.executor.ExecutorRegistry.get", _raise)

    tool = ExecutorTool()
    session = _observe_session()
    payload = {
        "executor_type": "missing",
        "command": ["python", "-c", "print('x')"],
        "cwd": str(tmp_path),
    }

    with pytest.raises(UserInputError, match="unknown executor_type"):
        tool.run(payload, session)


def test_executor_tool_enforces_session_capability(monkeypatch, tmp_path):
    backend = _FakeBackend()
    monkeypatch.setattr("openrat.tools.executor.ExecutorRegistry.get", lambda name: backend)

    session = Session(
        autonomy=AutonomyLevel.OBSERVE,
        patch_policy="interactive",
        user_approvals={"params.modify"},
    )

    tool = ExecutorTool()
    payload = {
        "executor_type": "docker",
        "command": ["python", "-c", "print('x')"],
        "cwd": str(tmp_path),
    }

    with pytest.raises(PolicyViolation):
        tool.run(payload, session)


def test_executor_tool_wraps_backend_exception(monkeypatch, tmp_path):
    backend = _FakeBackend(boom=True)
    monkeypatch.setattr("openrat.tools.executor.ExecutorRegistry.get", lambda name: backend)

    tool = ExecutorTool()
    session = _observe_session()
    payload = {
        "executor_type": "docker",
        "command": ["python", "-c", "print('x')"],
        "cwd": str(tmp_path),
    }

    with pytest.raises(ExecutionError, match="executor backend failed"):
        tool.run(payload, session)


def test_executor_tool_registers_and_executes_via_registry(monkeypatch, tmp_path):
    backend = _FakeBackend()
    monkeypatch.setattr("openrat.tools.executor.ExecutorRegistry.get", lambda name: backend)

    session = _observe_session()
    registry = ToolRegistry(session=session)
    tool = ExecutorTool()

    registry.register(
        "executor",
        lambda args: tool.run(args, session),
        capability=tool.capability,
    )

    result = registry.execute(
        "executor",
        {
            "executor_type": "docker",
            "command": ["python", "-c", "print('registry')"],
            "cwd": str(tmp_path),
        },
    )

    assert result["status"] == "completed"
    assert backend.calls
