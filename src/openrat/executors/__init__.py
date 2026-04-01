"""Executor backends and registry.

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
from .registry import ExecutorRegistry as _ExecutorRegistry
from openrat.core.errors import UserInputError

EXECUTOR_POLICY = {"mode": "production"}


def set_executor_policy(mode: str):
    if mode not in ("production", "auto"):
        raise UserInputError("unsupported executor policy mode; only 'production' is allowed")
    EXECUTOR_POLICY["mode"] = "production"
    ExecutorRegistry.clear()
    ExecutorRegistry.register("docker", DockerExecutor())


ExecutorRegistry = _ExecutorRegistry()
set_executor_policy("production")

__all__ = [
    "ExecutorRegistry",
    "set_executor_policy",
    "EXECUTOR_POLICY",
    "DockerExecutor",
]
