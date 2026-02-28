from typing import Dict, Any, Optional, List
from .base_executor import BaseExecutor
import subprocess
import time
from pathlib import Path


class DockerExecutor(BaseExecutor):
    """Stubbed Docker executor that returns a scheduling acknowledgement."""

    def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
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

    def _build_docker_cmd(self, command: List[str], cwd: Optional[str]) -> List[str]:
        cwd_path = Path(cwd) if cwd else Path.cwd()
        # mount the cwd into the container at the same path
        return [
            "docker",
            "run",
            "--rm",
            "-v",
            f"{cwd_path}:{cwd_path}",
            "-w",
            str(cwd_path),
            self.image,
        ] + command

    def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        command = payload.get("command")
        cwd = payload.get("cwd")
        timeout = payload.get("timeout")

        docker_cmd = self._build_docker_cmd(command, cwd)

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
            stdout = e.stdout or ""
            stderr = (e.stderr or "") + "\nDocker process timed out."

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