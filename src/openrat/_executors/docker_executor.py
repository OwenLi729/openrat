from collections.abc import Mapping
from typing import Any
from .base_executor import BaseExecutor
import subprocess
import time
from pathlib import Path
import os
import re

from openrat.core.errors import UserInputError
from openrat.sandbox.guardrails import validate_command_guardrails


DEFAULT_TIMEOUT_SECONDS = 300
MAX_TIMEOUT_SECONDS = 3600
DEFAULT_MEMORY_LIMIT = "512m"
MAX_MEMORY_BYTES = 4 * 1024 * 1024 * 1024  # 4 GiB
DEFAULT_CPU_LIMIT = "1.0"
MAX_CPU_LIMIT = 4.0
_MEMORY_RE = re.compile(r"^(\d+)([mMgG])$")


def _to_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


class DockerExecutor(BaseExecutor):
    """Production Docker executor.

    All Openrat execution is expected to route through this executor.
    """

    def __init__(self, image: str = "python:3.11"):
        self.image = image

    def _memory_to_bytes(self, value: str) -> int:
        match = _MEMORY_RE.match(value.strip())
        if not match:
            raise UserInputError("memory must match '<number><m|g>', e.g. '512m' or '1g'")

        amount = int(match.group(1))
        unit = match.group(2).lower()
        if amount <= 0:
            raise UserInputError("memory must be greater than zero")
        if unit == "m":
            return amount * 1024 * 1024
        return amount * 1024 * 1024 * 1024

    def _normalized_limits(self, payload: Mapping[str, Any]) -> tuple[int | None, str | None, str | None]:
        allow_unbounded = bool(payload.get("allow_unbounded_limits", False))

        timeout = payload.get("timeout")
        if timeout is None:
            timeout_limit = None if allow_unbounded else DEFAULT_TIMEOUT_SECONDS
        else:
            if not isinstance(timeout, int) or timeout <= 0:
                raise UserInputError("timeout must be a positive integer")
            if not allow_unbounded and timeout > MAX_TIMEOUT_SECONDS:
                raise UserInputError(f"timeout must be <= {MAX_TIMEOUT_SECONDS} seconds")
            timeout_limit = timeout

        limits = payload.get("limits", {}) or {}
        memory = str(limits.get("memory") or DEFAULT_MEMORY_LIMIT).strip().lower()
        cpus = str(limits.get("cpus") or DEFAULT_CPU_LIMIT).strip().lower()

        if memory in {"none", "unbounded", "unlimited"}:
            if not allow_unbounded:
                raise UserInputError("unbounded memory requires explicit allow_unbounded_limits opt-in")
            memory_limit = None
        else:
            memory_bytes = self._memory_to_bytes(memory)
            if memory_bytes > MAX_MEMORY_BYTES:
                raise UserInputError("memory exceeds maximum allowed limit of 4g")
            memory_limit = memory

        if cpus in {"none", "unbounded", "unlimited"}:
            if not allow_unbounded:
                raise UserInputError("unbounded CPU requires explicit allow_unbounded_limits opt-in")
            cpu_limit = None
        else:
            try:
                cpu_value = float(cpus)
            except ValueError as exc:
                raise UserInputError("cpus must be a numeric string") from exc
            if cpu_value <= 0:
                raise UserInputError("cpus must be greater than zero")
            if cpu_value > MAX_CPU_LIMIT:
                raise UserInputError(f"cpus must be <= {MAX_CPU_LIMIT}")
            cpu_limit = cpus

        return timeout_limit, memory_limit, cpu_limit

    def _build_docker_cmd(
        self,
        command: list[str],
        payload: Mapping[str, Any],
        *,
        memory_limit: str | None,
        cpu_limit: str | None,
    ) -> list[str]:
        code_dir = payload.get("code_dir")
        outputs_dir = payload.get("outputs_dir")

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
            "--cap-drop",
            "ALL",
            "--read-only",
            "--tmpfs",
            "/tmp:rw,noexec,nosuid,nodev,size=64m",
            "--pids-limit",
            "100",
            "-u",
            f"{uid}:{gid}",
        ]

        if memory_limit is not None:
            cmd += ["--memory", str(memory_limit)]
        if cpu_limit is not None:
            cmd += ["--cpus", str(cpu_limit)]

        if code_dir:
            cmd += ["-v", f"{Path(code_dir)}:/code:ro"]
        if outputs_dir:
            cmd += ["-v", f"{Path(outputs_dir)}:/outputs:rw"]

        if outputs_dir:
            cmd += ["-w", "/outputs"]

        cmd += [self.image]
        cmd += command
        return cmd

    def execute(self, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        command = payload.get("command")
        validate_command_guardrails(command)

        timeout, memory_limit, cpu_limit = self._normalized_limits(payload)
        cwd = payload.get("cwd")

        docker_cmd = self._build_docker_cmd(
            command,
            payload,
            memory_limit=memory_limit,
            cpu_limit=cpu_limit,
        )

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
            "executor": "docker",
            "command": docker_cmd,
            "cwd": cwd,
            "timeout": timeout,
            "return_code": return_code,
            "stdout": stdout,
            "stderr": stderr,
            "timed_out": timed_out,
            "duration": end - start,
        }


ProductionDockerExecutor = DockerExecutor
