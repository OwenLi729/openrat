"""Executors package

Expose a registry `EXECUTORS` mapping executor_type -> executor instance.
"""
from .docker_executor import ProductionDockerExecutor, DockerExecutor
from .registry import ExecutorRegistry

# create a registry and pre-register allowed executors at startup
_REGISTRY = ExecutorRegistry()
_REGISTRY.register("docker", ProductionDockerExecutor())

# backward-compatible mapping used by existing tests and code
EXECUTORS = {name: _REGISTRY.get(name) for name in _REGISTRY.list()}

__all__ = ["_REGISTRY", "EXECUTORS", "DockerExecutor", "ProductionDockerExecutor"]
