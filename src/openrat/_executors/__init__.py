
"""
Executor backends and registry.

This namespace is intentionally private and not part of the public API.

Internal module: Contains Docker and local execution strategies. Users
should not import from this module directly.

Executor configuration is handled via Openrat config dict:
    from openrat import Openrat
    
    app = Openrat({
        "executor": "docker",
        "docker_image": "python:3.11",
        "memory": "512m",
        "cpus": "1.0",
    })
"""

from .docker_executor import DockerExecutor
from .local_executor import LocalExecutor
from ._registry import ExecutorRegistry as _ExecutorRegistry
from openrat.core.errors import UserInputError

EXECUTOR_POLICY = {"mode": "production"}


def set_executor_policy(mode: str):
    if mode not in ("production", "auto"):
        raise UserInputError("unsupported executor policy mode; only 'production' is allowed")
    EXECUTOR_POLICY["mode"] = "production"
    ExecutorRegistry.clear()
    ExecutorRegistry.register("docker", DockerExecutor())
    ExecutorRegistry.register("local", LocalExecutor())


ExecutorRegistry = _ExecutorRegistry()
set_executor_policy("production")

__all__ = [
    "ExecutorRegistry",
    "set_executor_policy",
    "EXECUTOR_POLICY",
    "DockerExecutor",
    "LocalExecutor",
]
