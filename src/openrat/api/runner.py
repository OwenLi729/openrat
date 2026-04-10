from pathlib import Path
from collections.abc import Mapping
from typing import Any
import shutil
import tempfile
import re

from openrat.core.governance.autonomy import AutonomyLevel
from openrat.core.session.session import Session
from openrat._executors import DockerExecutor, LocalExecutor
from openrat.core.errors import UserInputError, EnvironmentError, InternalError, LocalExecutionBypassesSandboxError
from openrat.model.types import Message, ModelResponse
from openrat.core._protocols import ExecutorProtocol, ToolRegistryProtocol
from openrat._sandbox._guardrails import validate_command_guardrails


DEFAULT_TIMEOUT_SECONDS = 300
MAX_TIMEOUT_SECONDS = 3600
DEFAULT_MEMORY_LIMIT = "512m"
MAX_MEMORY_BYTES = 4 * 1024 * 1024 * 1024  # 4 GiB
DEFAULT_CPU_LIMIT = "1.0"
MAX_CPU_LIMIT = 4.0
_MEMORY_RE = re.compile(r"^(\d+)([mMgG])$")


def validate_experiment_path(path: str) -> Path:
    """Validate and normalize an experiment file path.
    
    Internal utility; not part of public API.
    
    Raises:
        EnvironmentError: If path is outside cwd or does not exist.
    """
    p = Path(path)
    if not p.exists():
        raise EnvironmentError(f"Experiment file not found: {path}")
    p = p.resolve()
    cwd = Path.cwd().resolve()
    try:
        p.relative_to(cwd)
    except ValueError:
        # restrict running experiments outside current working directory
        # Invalid experiment path currently mapped to EnvironmentError. This could also be argued as UserInputError.
        raise EnvironmentError("Experiment path must live inside the current working directory")
    return p


# Backward-compatible alias (private name indicates legacy)
_validate_experiment_path = validate_experiment_path


def _choose_executor(preferred: str | None, docker_image: str) -> tuple[str, ExecutorProtocol]:
    if preferred is not None and preferred not in {"docker", "local"}:
        raise UserInputError(
            f"unsupported executor '{preferred}'",
            hint="Supported executors: 'docker' (default), 'local' (trusted-host only).",
        )

    if preferred == "local":
        return "local", LocalExecutor()

    if not shutil.which("docker"):
        raise EnvironmentError(
            "docker executor requested but docker is not available",
            hint="Install Docker or explicitly opt into executor='local' for trusted-host execution.",
        )

    return "docker", DockerExecutor(image=docker_image)


def _validate_managed_mount_path(path: Path, *, allowed_base: Path, label: str) -> str:
    resolved = path.resolve()
    base = allowed_base.resolve()
    if not resolved.exists() or not resolved.is_dir():
        raise InternalError(f"managed {label} must be an existing directory")
    try:
        resolved.relative_to(base)
    except ValueError as exc:
        raise InternalError(f"managed {label} escaped allowed execution base") from exc
    if resolved.is_symlink():
        raise InternalError(f"managed {label} must not be a symlink")
    return str(resolved)


def _memory_to_bytes(value: str) -> int:
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


def _normalize_timeout(timeout: int | None, *, allow_unbounded_limits: bool) -> int | None:
    if timeout is None:
        if allow_unbounded_limits:
            return None
        return DEFAULT_TIMEOUT_SECONDS

    if not isinstance(timeout, int) or timeout <= 0:
        raise UserInputError("timeout must be a positive integer")

    if not allow_unbounded_limits and timeout > MAX_TIMEOUT_SECONDS:
        raise UserInputError(f"timeout must be <= {MAX_TIMEOUT_SECONDS} seconds")

    return timeout


def _normalize_limits(
    *,
    timeout: int | None,
    memory: str,
    cpus: str,
    allow_unbounded_limits: bool,
) -> tuple[int | None, str, str]:
    normalized_timeout = _normalize_timeout(timeout, allow_unbounded_limits=allow_unbounded_limits)

    memory_limit = str(memory or DEFAULT_MEMORY_LIMIT).strip().lower()
    if memory_limit in {"none", "unbounded", "unlimited"}:
        if not allow_unbounded_limits:
            raise UserInputError("unbounded memory requires explicit allow_unbounded_limits opt-in")
    else:
        memory_bytes = _memory_to_bytes(memory_limit)
        if memory_bytes > MAX_MEMORY_BYTES:
            raise UserInputError("memory exceeds maximum allowed limit of 4g")

    cpu_limit = str(cpus or DEFAULT_CPU_LIMIT).strip().lower()
    if cpu_limit in {"none", "unbounded", "unlimited"}:
        if not allow_unbounded_limits:
            raise UserInputError("unbounded CPU requires explicit allow_unbounded_limits opt-in")
    else:
        try:
            cpu_value = float(cpu_limit)
        except ValueError as exc:
            raise UserInputError("cpus must be a numeric string") from exc

        if cpu_value <= 0:
            raise UserInputError("cpus must be greater than zero")
        if cpu_value > MAX_CPU_LIMIT:
            raise UserInputError(f"cpus must be <= {MAX_CPU_LIMIT}")

    return normalized_timeout, memory_limit, cpu_limit


def run(
    path: str,
    *,
    executor: str | None = None,
    timeout: int | None = None,
    docker_image: str = "python:3.11",
    isolate: bool = True,
    memory: str = "512m",
    cpus: str = "1.0",
    allow_unbounded_limits: bool = False,
) -> Mapping[str, Any]:
    """Internal direct execution helper (not part of public API).
    
    By default this will copy the experiment into a per-run ephemeral directory
    and execute inside that directory to limit filesystem access. The runner will
    create separate `code/` (read-only) and `outputs/` (writable) mounts for Docker.
    """
    p = validate_experiment_path(path)
    executor_name, exec_obj = _choose_executor(executor, docker_image)

    timeout_limit, memory_limit, cpu_limit = _normalize_limits(
        timeout=timeout,
        memory=memory,
        cpus=cpus,
        allow_unbounded_limits=allow_unbounded_limits,
    )

    if isolate:
        with tempfile.TemporaryDirectory(prefix="openrat-run-") as td:
            td_path = Path(td)
            code_dir = td_path / "code"
            outputs_dir = td_path / "outputs"
            code_dir.mkdir()
            outputs_dir.mkdir()
            # copy experiment into code subdir
            dest = code_dir / p.name
            shutil.copy2(p, dest)

            if executor_name == "docker":
                command = ["python", f"/code/{dest.name}"]
            else:
                command = ["python", str(dest)]
            validate_command_guardrails(command)

            payload = {
                "command": command,
                "cwd": str(outputs_dir),
                "timeout": timeout_limit,
                "limits": {"memory": memory_limit, "cpus": cpu_limit},
                "allow_unbounded_limits": allow_unbounded_limits,
            }
            if executor_name == "docker":
                payload["code_dir"] = _validate_managed_mount_path(code_dir, allowed_base=td_path, label="code_dir")
                payload["outputs_dir"] = _validate_managed_mount_path(outputs_dir, allowed_base=td_path, label="outputs_dir")

            result = exec_obj.execute(payload)
            if executor_name == "local":
                result = dict(result)
                result["security_error"] = LocalExecutionBypassesSandboxError.DEFAULT_MESSAGE
            return result

    command = ["python", str(p)]
    validate_command_guardrails(command)

    payload = {
        "command": command,
        "cwd": str(p.parent),
        "timeout": timeout_limit,
        "limits": {"memory": memory_limit, "cpus": cpu_limit},
        "allow_unbounded_limits": allow_unbounded_limits,
    }

    result = exec_obj.execute(payload)
    if executor_name == "local":
        result = dict(result)
        result["security_error"] = LocalExecutionBypassesSandboxError.DEFAULT_MESSAGE
    return result


class OpenRatAgent:
    """Internal runtime adapter (not part of public API).

    Provides direct execution and LLM agent loop capabilities.
    Internal use only; use Openrat facade for public workflows.

    Configuration:
      - Execution keys (``executor``, ``docker_image``) for direct paths
      - Model keys (``provider``, ``api_key``, ``model_name``) for LLM loop
    """

    def __init__(self, config: Mapping[str, Any] | None = None):
        self.config = dict(config or {})
        self.executor = self.config.get("executor")
        self.docker_image = self.config.get("docker_image", "python:3.11")
        self.allow_unbounded_limits = bool(self.config.get("allow_unbounded_limits", False))
        self._selected_executor_name = "docker" if self.executor is None else str(self.executor)

        session_from_config = self.config.get("session")
        if isinstance(session_from_config, Session):
            self.session = session_from_config
        else:
            autonomy_raw = self.config.get("autonomy", AutonomyLevel.OBSERVE)
            autonomy = autonomy_raw if isinstance(autonomy_raw, AutonomyLevel) else AutonomyLevel(int(autonomy_raw))
            self.session = Session(
                autonomy=autonomy,
                patch_policy=str(self.config.get("patch_policy", "disabled")),
                user_approvals=set(self.config.get("user_approvals") or set()),
            )

        # Build the LLM agent loop only when a model provider is configured.
        self.agent_loop: Any = None
        self.tool_registry: ToolRegistryProtocol | None = None
        if self.config.get("provider"):
            from openrat.model._factory import ModelFactory
            from openrat.model._agent_loop import AgentLoop
            from openrat.tools.registry import ToolRegistry

            adapter = ModelFactory.create(self.config)
            self.tool_registry = ToolRegistry(session=self.session)

            # Register the execution runner as callable tool for the model.
            _self = self

            def run_experiment(arguments: Mapping[str, Any]) -> Mapping[str, Any]:
                path = arguments.get("path")
                if not path:
                    return {"status": "error", "reason": "path is required"}
                return _self.run(
                    path,
                    timeout=arguments.get("timeout"),
                    isolate=arguments.get("isolate", True),
                    memory=arguments.get("memory", "512m"),
                    cpus=arguments.get("cpus", "1.0"),
                )

            run_experiment.capability = "observe"
            run_experiment.__openrat_trusted__ = True

            self.tool_registry.register(
                "run_experiment",
                run_experiment,
                capability="observe",
                trusted=True,
            )
            self.agent_loop = AgentLoop(adapter, tool_registry=self.tool_registry)

    def run(self, path: str, timeout: int | None = None, isolate: bool = True, memory: str = "512m", cpus: str = "1.0") -> Mapping[str, Any]:
        """Internal direct execution (not part of public API)."""
        self.session.authorize(
            "observe",
            action="runner.run",
            metadata={"path": path, "executor": self._selected_executor_name},
        )
        return run(
            path,
            executor=self.executor,
            timeout=timeout,
            docker_image=self.docker_image,
            isolate=isolate,
            memory=memory,
            cpus=cpus,
            allow_unbounded_limits=self.allow_unbounded_limits,
        )

    def chat(self, messages: str | list[Message], max_turns: int = 10) -> ModelResponse:
        """Internal LLM agent loop (not part of public API).

        ``messages`` can be:
        - a plain string (converted to a single user Message), or
        - a list of ``openrat.model.types.Message`` objects.

        Requires ``provider`` (and usually ``api_key``, ``model_name``) in config.
        """
        if self.agent_loop is None:
            raise UserInputError(
                "No model configured. Pass 'provider', 'api_key', and 'model_name' "
                "in the config dict to enable the LLM agent loop."
            )
        from openrat.model.types import Message as _Message
        if isinstance(messages, str):
            messages = [_Message(role="user", content=messages)]
        return self.agent_loop.run(list(messages), max_turns=max_turns)
