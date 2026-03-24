from pathlib import Path
from collections.abc import Mapping
from typing import Any
import shutil
import tempfile

from openrat.executors import LocalExecutor, ProductionDockerExecutor
from openrat.errors import UserInputError, EnvironmentError
from openrat.model.types import Message, ModelResponse
from openrat.protocols import ExecutorProtocol, ToolRegistryProtocol


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


def _choose_executor(preferred: str | None, docker_image: str) -> ExecutorProtocol:
    # prefer docker when available unless explicitly asked for local
    if preferred is not None and preferred not in {"local", "docker"}:
        raise UserInputError(
            f"unsupported executor '{preferred}'",
            hint="Use one of: local, docker",
        )

    if preferred == "local":
        return LocalExecutor()

    if preferred == "docker":
        if not shutil.which("docker"):
            raise EnvironmentError(
                "docker executor requested but docker is not available",
                hint="Install Docker or use executor='local'.",
            )
        return ProductionDockerExecutor(image=docker_image)

    if shutil.which("docker"):
        return ProductionDockerExecutor(image=docker_image)

    return LocalExecutor()


def run(path: str, *, executor: str | None = None, timeout: int | None = None, docker_image: str = "python:3.11", isolate: bool = True, memory: str = "512m", cpus: str = "1.0") -> Mapping[str, Any]:
    """Internal direct execution helper (not part of public API).
    
    By default this will copy the experiment into a per-run ephemeral directory
    and execute inside that directory to limit filesystem access. The runner will
    create separate `code/` (read-only) and `outputs/` (writable) mounts for Docker.
    """
    p = validate_experiment_path(path)
    exec_obj = _choose_executor(executor, docker_image)

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

            payload = {
                # run using container-local paths
                "command": ["python", f"/code/{dest.name}"],
                "cwd": str(outputs_dir),
                "timeout": timeout,
                "code_dir": str(code_dir),
                "outputs_dir": str(outputs_dir),
                "limits": {"memory": memory, "cpus": cpus},
            }
            result = exec_obj.execute(payload)
            return result

    payload = {
        "command": ["python", str(p)],
        "cwd": str(p.parent),
        "timeout": timeout,
    }

    result = exec_obj.execute(payload)
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

        # Build the LLM agent loop only when a model provider is configured.
        self.agent_loop: Any = None
        self.tool_registry: ToolRegistryProtocol | None = None
        if self.config.get("provider"):
            from openrat.model.factory import ModelFactory
            from openrat.model.agent_loop import AgentLoop
            from openrat.tools.registry import ToolRegistry

            adapter = ModelFactory.create(self.config)
            self.tool_registry = ToolRegistry()

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

            self.tool_registry.register("run_experiment", run_experiment)
            self.agent_loop = AgentLoop(adapter, tool_registry=self.tool_registry)

    def run(self, path: str, timeout: int | None = None, isolate: bool = True, memory: str = "512m", cpus: str = "1.0") -> Mapping[str, Any]:
        """Internal direct execution (not part of public API)."""
        return run(path, executor=self.executor, timeout=timeout, docker_image=self.docker_image, isolate=isolate, memory=memory, cpus=cpus)

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
