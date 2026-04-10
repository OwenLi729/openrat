import sys
from pathlib import Path
import subprocess

# ensure project root
root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root))

from openrat._executors import ExecutorRegistry
from openrat.tools.executor import ExecutorTool
from openrat.core.governance.autonomy import AutonomyLevel
from openrat.core.session.session import Session
from openrat.core.errors import LocalExecutionBypassesSandboxError


def test_registry_contains_docker_default_and_local_explicit():
    assert ExecutorRegistry.list() == ["docker", "local"]


def test_tools_executor_routes_to_docker(monkeypatch):
    tool = ExecutorTool()
    
    project_root = Path(__file__).resolve().parents[2]
    
    # Create session with observe-level autonomy
    session = Session(autonomy=AutonomyLevel.OBSERVE, patch_policy="disabled", user_approvals={"observe"})

    # stub subprocess.run for docker
    completed = subprocess.CompletedProcess(args=["docker"], returncode=0, stdout="ok", stderr="")
    monkeypatch.setattr("subprocess.run", lambda *a, **k: completed)

    payload = {
        "executor_type": "docker",
        "command": ["python", "script.py"],
        "cwd": str(project_root),
        "timeout": 1,
    }
    res = tool.run(payload, session)
    assert res["executor"] == "docker"
    assert res["return_code"] == 0


def test_tools_executor_routes_to_local_only_when_explicit(monkeypatch, tmp_path):
    tool = ExecutorTool()
    session = Session(autonomy=AutonomyLevel.OBSERVE, patch_policy="disabled", user_approvals={"observe"})

    completed = subprocess.CompletedProcess(args=["python", "script.py"], returncode=0, stdout="ok", stderr="")
    monkeypatch.setattr("subprocess.run", lambda *a, **k: completed)

    payload = {
        "executor_type": "local",
        "command": ["python", "script.py"],
        "cwd": str(tmp_path),
        "timeout": 1,
    }
    res = tool.run(payload, session)
    assert res["executor"] == "local"
    assert res["security_error"] == LocalExecutionBypassesSandboxError.DEFAULT_MESSAGE