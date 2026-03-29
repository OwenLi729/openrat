from pathlib import Path
from collections.abc import Mapping
from typing import Any

from .base import BaseTool, ToolProposal
from openrat.executors import ExecutorRegistry
from openrat.core.errors import UserInputError, ExecutionError


class ExecutorTool(BaseTool):
    """Execute commands by delegating to a configured executor backend."""

    name = "executor"
    description = "delegate command execution to registered executor backends"
    capability = "observe"
    required_autonomy_level = 0

    MAX_TIMEOUT = 3600

    def _validate_payload(self, payload: Mapping[str, Any]) -> None:
        if not isinstance(payload, Mapping):
            raise UserInputError("payload must be a mapping")

        allowed_keys = {
            "executor_type",
            "command",
            "cwd",
            "timeout",
            "code_dir",
            "outputs_dir",
            "limits",
        }
        extra = set(payload.keys()) - allowed_keys
        if extra:
            raise UserInputError(f"unexpected payload keys: {sorted(extra)}")

        executor_type = str(payload.get("executor_type", "docker"))
        try:
            ExecutorRegistry.get(executor_type)
        except KeyError as exc:
            raise UserInputError(f"unknown executor_type: {executor_type}") from exc

        command = payload.get("command")
        if not isinstance(command, list) or not command or not all(isinstance(part, str) for part in command):
            raise UserInputError("command must be a non-empty list[str]")

        cwd = payload.get("cwd")
        if cwd is not None:
            cwd_path = Path(str(cwd)).resolve()
            if not cwd_path.exists() or not cwd_path.is_dir():
                raise UserInputError("cwd must reference an existing directory")

        timeout = payload.get("timeout")
        if timeout is not None and (
            not isinstance(timeout, (int, float))
            or timeout <= 0
            or timeout > self.MAX_TIMEOUT
        ):
            raise UserInputError(f"timeout must be >0 and <= {self.MAX_TIMEOUT}")

        limits = payload.get("limits")
        if limits is not None and not isinstance(limits, Mapping):
            raise UserInputError("limits must be a mapping when provided")

    def run(self, payload: Mapping[str, Any], session: Any) -> Mapping[str, Any]:
        proposal = ToolProposal(
            tool_name=self.name,
            payload=payload,
            capability=self.capability,
        )
        self.governance = session
        self.validate(proposal)

        executor_type = str(payload.get("executor_type", "docker"))
        backend = ExecutorRegistry.get(executor_type)

        backend_payload = {
            "command": payload["command"],
            "cwd": payload.get("cwd"),
            "timeout": payload.get("timeout"),
            "code_dir": payload.get("code_dir"),
            "outputs_dir": payload.get("outputs_dir"),
            "limits": payload.get("limits", {}),
        }

        try:
            result = backend.execute(backend_payload)
        except Exception as exc:
            raise ExecutionError("executor backend failed", cause=exc) from exc

        if not isinstance(result, Mapping):
            raise ExecutionError("executor backend returned non-mapping result")

        return dict(result)


Executor = ExecutorTool
