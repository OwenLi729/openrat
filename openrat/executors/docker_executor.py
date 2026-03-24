from collections.abc import Mapping
from typing import Any
from .base_executor import BaseExecutor
import subprocess
import time
from pathlib import Path
import os


def _to_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


class DockerExecutor(BaseExecutor):
    """Stubbed Docker executor that returns a scheduling acknowledgement."""

    def execute(self, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        return {
            "status": "scheduled",
            "executor": "docker",
            "command": payload.get("command"),
            "cwd": payload.get("cwd"),
            "timeout": payload.get("timeout"),
        }


class ProductionDockerExecutor(BaseExecutor):
    """A production executor that runs the command inside a Docker container.

    This uses the `docker` CLI and returns a serializable result dictionary.
    Unit tests should monkeypatch `subprocess.run` to avoid invoking Docker.
    """

    def __init__(self, image: str = "python:3.11"):
        self.image = image

    def _build_docker_cmd(self, command: list[str], payload: Mapping[str, Any]) -> list[str]:
        # payload may contain 'code_dir' and 'outputs_dir' (host paths), and 'limits'
        code_dir = payload.get("code_dir")
        outputs_dir = payload.get("outputs_dir")
        limits = payload.get("limits", {}) or {}

        uid = os.getuid()
        gid = os.getgid()

        cmd = [
            "docker",
            "run",
            "--rm",
            "--network",
            "none",
            "--security-opt",
            "no-new-privileges",
            "--pids-limit",
            "100",
            "-u",
            f"{uid}:{gid}",
        ]

        # resource limits
        mem = limits.get("memory")
        cpus = limits.get("cpus")
        if mem:
            cmd += ["--memory", str(mem)]
        if cpus:
            cmd += ["--cpus", str(cpus)]

        # mounts: mount code as read-only at /code, outputs as rw at /outputs
        if code_dir:
            cmd += ["-v", f"{Path(code_dir)}:/code:ro"]
        if outputs_dir:
            cmd += ["-v", f"{Path(outputs_dir)}:/outputs:rw"]

        # set working directory inside container to /outputs if provided
        workdir = "/outputs" if outputs_dir else None
        if workdir:
            cmd += ["-w", workdir]

        cmd += [self.image]
        cmd += command
        return cmd

    def execute(self, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        command = payload.get("command")
        timeout = payload.get("timeout")
        cwd = payload.get("cwd")

        docker_cmd = self._build_docker_cmd(command, payload)

        start = time.time()
        timed_out = False
        try:
            completed = subprocess.run(
                docker_cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return_code = completed.returncode
            stdout = completed.stdout
            stderr = completed.stderr
        except subprocess.TimeoutExpired as e:
            timed_out = True
            return_code = -1
            stdout = _to_text(e.stdout)
            stderr = _to_text(e.stderr) + "\nDocker process timed out."

        end = time.time()

        return {
            "status": "completed" if return_code == 0 and not timed_out else "failed",
            "executor": "docker_prod",
            "command": docker_cmd,
            "cwd": cwd,
            "timeout": timeout,
            "return_code": return_code,
            "stdout": stdout,
            "stderr": stderr,
            "timed_out": timed_out,
            "duration": end - start,
        }
