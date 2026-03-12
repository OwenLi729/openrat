from typing import Dict, Any
from .base_executor import BaseExecutor

try:
    from openrat.sandbox.exec import run_command
except ImportError:
    run_command = None  # type: ignore[assignment]


class LocalExecutor(BaseExecutor):
    """Executor that runs commands locally via `sandbox.exec.run_command`.

    This executor is intended for trusted environments (e.g., developer mode)
    and will invoke the sandbox execution helper. In unit tests monkeypatch
    ``openrat.executors.local_executor.run_command`` to avoid real subprocesses.
    """

    def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        # Resolve at call time so tests can patch the module-level name.
        import openrat.executors.local_executor as _self_mod
        _run_cmd = _self_mod.run_command

        if _run_cmd is None:
            return {"status": "unavailable", "reason": "run_command not installed"}

        cmd = payload.get("command")
        cwd = payload.get("cwd")
        timeout = payload.get("timeout")

        result = _run_cmd(cmd, cwd=cwd, timeout=timeout)

        return {
            "status": "completed" if result.succeeded else "failed",
            "return_code": result.return_code,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "timed_out": result.timed_out,
        }
