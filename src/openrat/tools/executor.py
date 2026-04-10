from pathlib import Path
from collections.abc import Mapping
from typing import Any
from pathlib import PurePosixPath

from .base import BaseTool, ToolProposal
from openrat._executors import ExecutorRegistry
from openrat.core.errors import UserInputError, ExecutionError
from openrat.sandbox.guardrails import validate_command_guardrails


class ExecutorTool(BaseTool):
    """Execute Python scripts via an explicitly selected backend with a fixed entrypoint.

    Security constraints:
    - shell entrypoints (sh/bash) are disallowed
    - inline execution flags (-c / -m) are disallowed
    - first token must be python/python3
    - second token must be a .py script path

    Docker remains the default and recommended backend. Local execution is
    available only when `executor_type="local"` is explicitly selected.
    """

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

        if payload.get("code_dir") is not None or payload.get("outputs_dir") is not None:
            raise UserInputError(
                "code_dir and outputs_dir are managed internally and cannot be provided"
            )

        executor_type = str(payload.get("executor_type", "docker"))
        try:
            ExecutorRegistry.get(executor_type)
        except KeyError as exc:
            raise UserInputError(f"unknown executor_type: {executor_type}") from exc

        command = payload.get("command")
        if not isinstance(command, list) or not command or not all(isinstance(part, str) for part in command):
            raise UserInputError("command must be a non-empty list[str]")

        validate_command_guardrails(command)

        executable = command[0].strip()
        if executable not in {"python", "python3"}:
            raise UserInputError("only python/python3 entrypoints are allowed")

        if len(command) < 2:
            raise UserInputError("command must include a script path as the second argument")

        script_target = command[1].strip()
        if script_target in {"-c", "-m", "-"} or script_target.startswith("-"):
            raise UserInputError("inline python execution is not allowed; pass a script path")

        script_path = PurePosixPath(script_target)
        if script_path.suffix != ".py":
            raise UserInputError("script target must end with .py")

        shell_tokens = {"sh", "bash", "zsh", "fish"}
        for token in command:
            if token.strip() in shell_tokens:
                raise UserInputError("shell entrypoints are not allowed")

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

        limits_input = payload.get("limits")
        if isinstance(limits_input, Mapping):
            memory = str(limits_input.get("memory") or "512m")
            cpus = str(limits_input.get("cpus") or "1.0")
        else:
            memory = "512m"
            cpus = "1.0"

        backend_payload = {
            "command": payload["command"],
            "cwd": payload.get("cwd"),
            "timeout": payload.get("timeout"),
            "limits": {"memory": memory, "cpus": cpus},
        }

        try:
            result = backend.execute(backend_payload)
        except Exception as exc:
            raise ExecutionError("executor backend failed", cause=exc) from exc

        if not isinstance(result, Mapping):
            raise ExecutionError("executor backend returned non-mapping result")

        return dict(result)


Executor = ExecutorTool
