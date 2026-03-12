import sys
from pathlib import Path
import pytest
import subprocess

# ensure project root
root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(root))

from openrat.executors import EXECUTORS
from openrat.executors.docker_executor import ProductionDockerExecutor


def test_docker_executor_schedulable():
    docker = EXECUTORS.get("docker")
    assert docker is not None
    payload = {"command": ["python", "a.py"], "cwd": ".", "timeout": 5}
    res = docker.execute(payload)
    assert res["status"] == "scheduled"
    assert res["executor"] == "docker"


def test_local_executor_calls_run_command(monkeypatch):
    local = EXECUTORS.get("local")
    assert local is not None

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

    def fake_run_command(cmd, cwd=None, timeout=None):
        assert cmd == ["python", "a.py"]
        return DummyResult()

    monkeypatch.setattr("openrat.executors.local_executor.run_command", fake_run_command)

    res = local.execute({"command": ["python", "a.py"], "cwd": ".", "timeout": 1})
    assert res["status"] == "completed"
    assert res["return_code"] == 0


def test_production_docker_timeout_bytes_are_coerced(monkeypatch):
    docker = ProductionDockerExecutor(image="python:3.11")

    def fake_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(
            cmd=["docker", "run"],
            timeout=1,
            output=b"partial stdout bytes",
            stderr=b"partial stderr bytes",
        )

    monkeypatch.setattr("subprocess.run", fake_run)

    result = docker.execute({"command": ["python", "a.py"], "cwd": ".", "timeout": 1})
    assert result["status"] == "failed"
    assert result["timed_out"] is True
    assert isinstance(result["stdout"], str)
    assert isinstance(result["stderr"], str)
    assert "Docker process timed out." in result["stderr"]