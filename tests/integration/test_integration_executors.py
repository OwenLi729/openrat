import sys
from pathlib import Path
import subprocess
import pytest

# ensure project root
root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root))

from executors import EXECUTORS
from tools.executor import Executor
from tools.base import ToolProposal


class MockGovernance:
    def __init__(self, autonomy_level=0, allow=True):
        self.autonomy_level = autonomy_level
        self._allow = allow

    def authorize_execution(self, proposal):
        return self._allow


def make_payload(executor_type):
    project_root = Path(__file__).resolve().parents[2]
    return {
        "executor_type": executor_type,
        "command": ["python", "script.py"],
        "cwd": str(project_root / "sandbox"),
        "timeout": 1,
    }


def test_registry_contains_expected():
    assert "docker" in EXECUTORS


def test_tools_executor_routes_all(monkeypatch):
    gov = MockGovernance(allow=True)
    tool = Executor(gov)

    # stub local run_command
    class DummyResult:
        def __init__(self):
            self.return_code = 0
            self.stdout = "ok"
            self.stderr = ""
            self.start_time = 0
            self.end_time = 1
            self.timed_out = False

        @property
        def duration(self):
            return self.end_time - self.start_time

        @property
        def succeeded(self):
            return self.return_code == 0 and not self.timed_out

    monkeypatch.setattr("executors.local_executor.run_command", lambda *a, **k: DummyResult())

    # stub subprocess.run for docker_prod
    completed = subprocess.CompletedProcess(args=["docker"], returncode=0, stdout="ok", stderr="")
    monkeypatch.setattr("subprocess.run", lambda *a, **k: completed)

    for name in list(EXECUTORS.keys()):
        payload = make_payload(name)
        proposal = ToolProposal(tool_name="executor", payload=payload)
        res = tool.execute(proposal)
        assert res is not None
        # production docker should run and return the subprocess return code
        if name == "docker":
            assert res.get("return_code") == 0