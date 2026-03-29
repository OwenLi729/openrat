import sys
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(root))

from openrat.executors import ExecutorRegistry
from openrat.executors.docker_executor import DockerExecutor


def test_registry_only_contains_docker():
    assert ExecutorRegistry.list() == ["docker"]


def test_docker_executor_runs_subprocess(monkeypatch):
    docker = ExecutorRegistry.get("docker")

    completed = subprocess.CompletedProcess(
        args=["docker", "run"],
        returncode=0,
        stdout="ok",
        stderr="",
    )
    monkeypatch.setattr("subprocess.run", lambda *a, **k: completed)

    payload = {
        "command": ["python", "/code/a.py"],
        "cwd": ".",
        "timeout": 5,
        "code_dir": "/tmp/code",
        "outputs_dir": "/tmp/out",
        "limits": {"memory": "256m", "cpus": "0.5"},
    }
    res = docker.execute(payload)
    assert res["status"] == "completed"
    assert res["executor"] == "docker"
    assert res["return_code"] == 0


def test_docker_timeout_bytes_are_coerced(monkeypatch):
    docker = DockerExecutor(image="python:3.11")

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