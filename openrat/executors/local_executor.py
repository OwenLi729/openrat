from typing import Dict, Any
from .base_executor import BaseExecutor

try:
    # Prefer the top-level shim so tests can monkeypatch `executors.local_executor.run_command`.
    from executors.local_executor import run_command
except Exception:
    try:
        from ..sandbox.exec import run_command
    except Exception:
        run_command = None


class LocalExecutor(BaseExecutor):
    """Executor that runs commands locally via `sandbox.exec.run_command`.

    This executor is intended for trusted environments (e.g., developer mode)
    and will invoke the sandbox execution helper. In unit tests we mock
    `run_command` to avoid actually launching processes.
    """

    def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        # resolve run_command at call time so tests can monkeypatch the shim
        try:
            from executors.local_executor import run_command as _run_cmd
        except Exception:
            try:
                from ..sandbox.exec import run_command as _run_cmd
            except Exception:
                _run_cmd = None

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
