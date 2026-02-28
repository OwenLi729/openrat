from typing import Dict, Any
from .base_executor import BaseExecutor

try:
    # import the local execution helper; it's allowed for executor backends
    from sandbox.exec import run_command
except Exception:
    run_command = None


class LocalExecutor(BaseExecutor):
    """Executor that runs commands locally via `sandbox.exec.run_command`.

    This executor is intended for trusted environments (e.g., developer mode)
    and will invoke the sandbox execution helper. In unit tests we mock
    `run_command` to avoid actually launching processes.
    """

    def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if run_command is None:
            return {"status": "unavailable", "reason": "run_command not installed"}

        cmd = payload.get("command")
        cwd = payload.get("cwd")
        timeout = payload.get("timeout")

        # run_command expects a list of strings
        result = run_command(cmd, cwd=cwd, timeout=timeout)

        return {
            "status": "completed" if result.succeeded else "failed",
            "return_code": result.return_code,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "timed_out": result.timed_out,
        }
