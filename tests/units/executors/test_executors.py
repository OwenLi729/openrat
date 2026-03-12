import sys
from pathlib import Path
import pytest

# ensure project root
root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(root))

from openrat.executors import EXECUTORS


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