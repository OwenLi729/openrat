# TO DO: Add other tools, build out executor tool
"""
This is a code execution tool. It will give the agent the ability to express the
intention of calling an Executor (built off of sandbox/exec.py which abstracts local execution).
Importantly, the model is not able to use the run tool to actually run the code. Instead, it can
express the intention of executing some file. Afterwards, policy management will deterministically check
the agent's permissions before executing the run. If the run is successful, the Executors will store
the trace of the run, which the agent can evaluate using the evaluate tool
"""

from tools.base import BaseTool, ToolProposal
from executors import _REGISTRY
from pathlib import Path
from typing import Dict, Any, List


class Executor(BaseTool):

    name = "Executor"
    description = "route execution proposals to registered executors"
    required_autonomy_level = 0

    # a minimal, configurable whitelist of allowed top-level commands
    DEFAULT_WHITELIST = {"python", "bash"}

    # maximum allowed timeout in seconds
    MAX_TIMEOUT = 3600

    def _validate_payload(self, payload: Dict[str, Any]):
        if not isinstance(payload, dict):
            raise TypeError("payload must be a dict")

        # only allow these keys from the agent; no docker flags or overrides
        allowed_keys = {"executor_type", "command", "cwd", "timeout"}
        extra = set(payload.keys()) - allowed_keys
        if extra:
            raise PermissionError(f"unexpected payload keys: {extra}")

        executor_type = payload.get("executor_type")
        if executor_type != "docker":
            raise ValueError("only 'docker' executor_type is allowed in production")

        # ensure executor is registered
        try:
            _REGISTRY.get(executor_type)
        except KeyError:
            raise ValueError(f"unknown executor_type: {executor_type}")

        command = payload.get("command")
        if not isinstance(command, list) or not command:
            raise ValueError("command must be a non-empty list")

        # validate command elements are plain strings and contain no shell metacharacters
        forbidden = set([";", "|", "&", "$", "<", ">", "`"])
        for part in command:
            if not isinstance(part, str):
                raise TypeError("command elements must be strings")
            if any(ch in part for ch in forbidden):
                raise PermissionError("command contains forbidden shell metacharacters")

        timeout = payload.get("timeout")
        if timeout is None:
            raise ValueError("timeout is required")
        if not isinstance(timeout, (int, float)) or timeout <= 0 or timeout > self.MAX_TIMEOUT:
            raise ValueError(f"timeout must be >0 and <= {self.MAX_TIMEOUT}")

        cwd = payload.get("cwd")
        if cwd is None:
            raise ValueError("cwd is required")
        cwd_path = Path(cwd).resolve()
        project_root = Path(__file__).resolve().parents[1]
        sandbox_root = (project_root / "sandbox").resolve()
        try:
            if not cwd_path.is_relative_to(sandbox_root):
                raise PermissionError("cwd must be inside the sandbox root")
        except AttributeError:
            if sandbox_root not in cwd_path.parents and cwd_path != sandbox_root:
                raise PermissionError("cwd must be inside the sandbox root")

    def execute(self, proposal: ToolProposal) -> Dict[str, Any]:
        # BaseTool.validate checks autonomy and payload semantics
        self.validate(proposal)

        # governance hook: allow governance engines to further authorize
        if hasattr(self.governance, "authorize_execution"):
            allowed = self.governance.authorize_execution(proposal)
            if not allowed:
                raise PermissionError("governance rejected execution proposal")

        payload = proposal.payload

        # Resolve backend deterministically from registry
        backend = _REGISTRY.get(payload["executor_type"])

        # build ExecutionSpec (simple dict here) and route to backend
        spec = {
            "command": payload["command"],
            "cwd": payload["cwd"],
            "timeout": payload["timeout"],
        }

        return backend.execute(spec)
