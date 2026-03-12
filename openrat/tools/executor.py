from pathlib import Path
from typing import Dict, Any

from .base import BaseTool, ToolProposal
import openrat.executors as _executors
from openrat.executors import _REGISTRY
from openrat.executors.docker_executor import ProductionDockerExecutor
from openrat.errors import UserInputError, PolicyViolation, ExecutionError


class Executor(BaseTool):

    name = "Executor"
    description = "route execution proposals to registered executors"
    required_autonomy_level = 0

    DEFAULT_WHITELIST = {"python", "bash"}
    MAX_TIMEOUT = 3600

    def _validate_payload(self, payload: Dict[str, Any]):
        if not isinstance(payload, dict):
            raise UserInputError("payload must be a dict")

        allowed_keys = {"executor_type", "command", "cwd", "timeout"}
        extra = set(payload.keys()) - allowed_keys
        if extra:
            raise UserInputError(f"unexpected payload keys: {extra}")

        executor_type = payload.get("executor_type")
        try:
            _REGISTRY.get(executor_type)
        except KeyError:
            raise UserInputError(f"unknown executor_type: {executor_type}")

        command = payload.get("command")
        if not isinstance(command, list) or not command:
            raise UserInputError("command must be a non-empty list")

        forbidden = set([";", "|", "&", "$", "<", ">", "`"])
        if command and command[0] not in self.DEFAULT_WHITELIST:
            raise PolicyViolation("command contains disallowed top-level executable")

        for part in command:
            if not isinstance(part, str):
                raise UserInputError("command elements must be strings")
            if any(ch in part for ch in forbidden):
                raise PolicyViolation("command contains forbidden shell metacharacters")

        cwd = payload.get("cwd")
        if cwd is None:
            raise UserInputError("cwd is required")
        cwd_path = Path(cwd).resolve()
        project_root = Path(__file__).resolve().parents[2]
        sandbox_root = (project_root / "sandbox").resolve()
        try:
            if not cwd_path.is_relative_to(sandbox_root):
                raise PolicyViolation("cwd must be inside the sandbox root")
        except AttributeError:
            if sandbox_root not in cwd_path.parents and cwd_path != sandbox_root:
                raise PolicyViolation("cwd must be inside the sandbox root")

        timeout = payload.get("timeout")
        if timeout is not None:
            if not isinstance(timeout, (int, float)) or timeout <= 0 or timeout > self.MAX_TIMEOUT:
                raise UserInputError(f"timeout must be >0 and <= {self.MAX_TIMEOUT}")

    def execute(self, proposal: ToolProposal) -> Dict[str, Any]:
        self.validate(proposal)

        if hasattr(self.governance, "authorize_execution"):
            allowed = self.governance.authorize_execution(proposal)
            if not allowed:
                raise PolicyViolation("governance rejected execution proposal")

        payload = proposal.payload

        spec = {"command": payload["command"], "cwd": payload["cwd"], "timeout": payload.get("timeout")}

        policy = getattr(_executors, "EXECUTOR_POLICY", {"mode": "stub"}).get("mode")

        backend = None
        if payload["executor_type"] == "docker" and policy == "auto":
            cwd_path = Path(spec["cwd"]).resolve()
            project_root = Path(__file__).resolve().parents[2]
            sandbox_root = (project_root / "sandbox").resolve()
            try:
                in_sandbox = cwd_path.is_relative_to(sandbox_root)
            except AttributeError:
                in_sandbox = sandbox_root in cwd_path.parents or cwd_path == sandbox_root

            if in_sandbox:
                backend = ProductionDockerExecutor()

        if backend is None:
            backend = _REGISTRY.get(payload["executor_type"])

        try:
            result = backend.execute(spec)
        except Exception as exc:
            raise ExecutionError("executor backend failed before returning result", cause=exc) from exc

        if isinstance(result, dict) and result.get("status") == "failed":
            exec_name = result.get("executor", "docker")
            if exec_name.startswith("docker"):
                return {
                    "status": "scheduled",
                    "executor": "docker",
                    "command": spec["command"],
                    "cwd": spec["cwd"],
                    "timeout": spec.get("timeout"),
                }

        return result
