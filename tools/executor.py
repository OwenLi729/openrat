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
from pathlib import Path
from typing import Dict, Any, List


class ExecutorBackend:
    """Abstract backend interface. Backends must NOT call subprocess directly
    when invoked by this router; they should enqueue or schedule work with the
    execution backend/daemon responsible for actually running code.
    """

    def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError()


class DockerExecutor(ExecutorBackend):
    def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        # In this prototype we DO NOT execute the command locally. Instead
        # return a scheduling acknowledgement that an execution request was
        # accepted by the router for a downstream docker executor.
        return {
            "status": "scheduled",
            "executor": "docker",
            "command": payload.get("command"),
            "cwd": payload.get("cwd"),
            "timeout": payload.get("timeout"),
        }


# Simple registry of available backends
_EXECUTORS: Dict[str, ExecutorBackend] = {
    "docker": DockerExecutor(),
}


class Executor(BaseTool):

    name = "Executor"
    description = "route execution proposals to registered executors"
    required_autonomy_level = 0

    # a minimal, configurable whitelist of allowed top-level commands
    DEFAULT_WHITELIST = {"python", "bash"}

    def _validate_payload(self, payload: Dict[str, Any]):
        if not isinstance(payload, dict):
            raise TypeError("payload must be a dict")

        executor_type = payload.get("executor_type")
        if not executor_type or executor_type not in _EXECUTORS:
            raise ValueError(f"unknown executor_type: {executor_type}")

        command = payload.get("command")
        if not isinstance(command, list) or not command:
            raise ValueError("command must be a non-empty list")

        # check whitelist: allow either bare command names or path-like
        first = command[0]
        if isinstance(first, str):
            first_name = Path(first).name
            if first_name not in self.DEFAULT_WHITELIST:
                raise PermissionError(f"command '{first_name}' is not whitelisted")
        else:
            raise TypeError("command elements must be strings")

        cwd = payload.get("cwd")
        if cwd is not None:
            cwd_path = Path(cwd).resolve()
            project_root = Path(__file__).resolve().parents[1]
            sandbox_root = (project_root / "sandbox").resolve()
            try:
                # Python 3.9+ has is_relative_to
                if not cwd_path.is_relative_to(sandbox_root):
                    raise PermissionError("cwd must be inside the sandbox root")
            except AttributeError:
                # fallback for older Python versions
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
        backend = _EXECUTORS[payload["executor_type"]]

        # route to backend (does not run subprocess locally)
        return backend.execute(payload)
