import sys
from pathlib import Path
import subprocess
import pytest

root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(root))

from openrat._executors import ExecutorRegistry
from openrat._executors.docker_executor import DockerExecutor
from openrat._executors.local_executor import LocalExecutor
from openrat.core.errors import LocalExecutionBypassesSandboxError


def test_registry_contains_docker_and_local():
    assert ExecutorRegistry.list() == ["docker", "local"]


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


def test_docker_executor_includes_hardening_flags(monkeypatch):
    captured = {"cmd": None}

    def _fake_run(cmd, *args, **kwargs):
        captured["cmd"] = list(cmd)
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr("subprocess.run", _fake_run)

    docker = DockerExecutor(image="python:3.11")
    docker.execute(
        {
            "command": ["python", "/code/a.py"],
            "cwd": ".",
            "timeout": 5,
            "code_dir": "/tmp/code",
            "outputs_dir": "/tmp/out",
            "limits": {"memory": "256m", "cpus": "0.5"},
        }
    )

    assert captured["cmd"] is not None
    assert "--cap-drop" in captured["cmd"]
    assert "ALL" in captured["cmd"]
    assert "--read-only" in captured["cmd"]
    assert "--tmpfs" in captured["cmd"]


def test_docker_executor_defaults_timeout_when_none(monkeypatch):
    docker = DockerExecutor(image="python:3.11")

    def _fake_run(*args, **kwargs):
        assert kwargs["timeout"] == 300
        return subprocess.CompletedProcess(args=args[0], returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr("subprocess.run", _fake_run)
    docker.execute({"command": ["python", "/code/a.py"], "cwd": ".", "timeout": None})


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


def test_local_executor_runs_subprocess(monkeypatch, tmp_path):
    local = ExecutorRegistry.get("local")

    completed = subprocess.CompletedProcess(
        args=["python", "hello.py"],
        returncode=0,
        stdout="ok",
        stderr="",
    )
    monkeypatch.setattr("subprocess.run", lambda *a, **k: completed)

    payload = {
        "command": ["python", "hello.py"],
        "cwd": str(tmp_path),
        "timeout": 5,
        "limits": {"memory": "256m", "cpus": "0.5"},
    }
    res = local.execute(payload)
    assert res["status"] == "completed"
    assert res["executor"] == "local"
    assert res["sandboxed"] is False
    assert res["security_error"] == LocalExecutionBypassesSandboxError.DEFAULT_MESSAGE


def test_local_executor_blocks_shell_entrypoints(tmp_path):
    local = LocalExecutor()

    with pytest.raises(Exception, match="shell entrypoints are not allowed"):
        local.execute({
            "command": ["bash", "script.sh"],
            "cwd": str(tmp_path),
            "timeout": 5,
        })