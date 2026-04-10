from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any
import subprocess
import time
import re

from .base_executor import BaseExecutor
from openrat.core.errors import UserInputError, LocalExecutionBypassesSandboxError
from openrat._sandbox._guardrails import validate_command_guardrails


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


class LocalExecutor(BaseExecutor):
    """Host execution backend for trusted, explicit workflows only.

    This executor is intentionally marked unsafe because it executes directly on
    the local machine and therefore does not provide container isolation.
    """

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

    def _normalized_limits(self, payload: Mapping[str, Any]) -> tuple[int | None, int | None, int | None]:
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
            memory_bytes = None
        else:
            memory_bytes = self._memory_to_bytes(memory)
            if memory_bytes > MAX_MEMORY_BYTES:
                raise UserInputError("memory exceeds maximum allowed limit of 4g")

        if cpus in {"none", "unbounded", "unlimited"}:
            if not allow_unbounded:
                raise UserInputError("unbounded CPU requires explicit allow_unbounded_limits opt-in")
            cpu_seconds = None
        else:
            try:
                cpu_value = float(cpus)
            except ValueError as exc:
                raise UserInputError("cpus must be a numeric string") from exc
            if cpu_value <= 0:
                raise UserInputError("cpus must be greater than zero")
            if cpu_value > MAX_CPU_LIMIT:
                raise UserInputError(f"cpus must be <= {MAX_CPU_LIMIT}")
            if timeout_limit is None:
                cpu_seconds = None
            else:
                cpu_seconds = max(1, int(cpu_value * timeout_limit))

        return timeout_limit, memory_bytes, cpu_seconds

    def _validate_local_command(self, command: list[str]) -> None:
        validate_command_guardrails(command)
        shell_tokens = {"sh", "bash", "zsh", "fish"}
        executable = command[0].strip() if command else ""
        if executable in shell_tokens:
            raise UserInputError("shell entrypoints are not allowed for local executor")
        if len(command) >= 2 and command[1].strip() in {"-c", "-m", "-"}:
            raise UserInputError("inline interpreter execution is not allowed for local executor")

    def execute(self, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        raw_command = payload.get("command")
        if not isinstance(raw_command, list) or not raw_command or not all(isinstance(p, str) for p in raw_command):
            raise UserInputError("command must be a non-empty list[str]")
        command = list(raw_command)
        self._validate_local_command(command)

        timeout, memory_bytes, cpu_seconds = self._normalized_limits(payload)

        cwd = payload.get("cwd")
        if cwd is not None:
            cwd_path = Path(str(cwd)).resolve()
            if not cwd_path.exists() or not cwd_path.is_dir():
                raise UserInputError("cwd must reference an existing directory")

        preexec_fn = None
        resource_limits_applied = False
        resource_limits_error: str | None = None

        if memory_bytes is not None or cpu_seconds is not None:
            try:
                import resource

                def _apply_limits() -> None:
                    if memory_bytes is not None:
                        resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, memory_bytes))
                    if cpu_seconds is not None:
                        resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds))

                preexec_fn = _apply_limits
                resource_limits_applied = True
            except Exception as exc:
                resource_limits_error = f"best-effort local resource limits unavailable: {exc}"

        start = time.time()
        timed_out = False
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(cwd) if cwd is not None else None,
                preexec_fn=preexec_fn,
            )
            return_code = completed.returncode
            stdout = completed.stdout
            stderr = completed.stderr
        except subprocess.TimeoutExpired as e:
            timed_out = True
            return_code = -1
            stdout = _to_text(e.stdout)
            stderr = _to_text(e.stderr) + "\nLocal process timed out."

        end = time.time()

        return {
            "status": "completed" if return_code == 0 and not timed_out else "failed",
            "executor": "local",
            "command": command,
            "cwd": str(cwd) if cwd is not None else None,
            "timeout": timeout,
            "return_code": return_code,
            "stdout": stdout,
            "stderr": stderr,
            "timed_out": timed_out,
            "duration": end - start,
            "sandboxed": False,
            "security_error": LocalExecutionBypassesSandboxError.DEFAULT_MESSAGE,
            "resource_limits_applied": resource_limits_applied,
            "resource_limits_error": resource_limits_error,
        }
