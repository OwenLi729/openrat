from .docker_executor import ProductionDockerExecutor, DockerExecutor
from .local_executor import LocalExecutor
from .registry import ExecutorRegistry as _ExecutorRegistry
from openrat.errors import UserInputError

"""Executor registry and policy configuration.

Public API:
  - ExecutorRegistry: Global singleton for executor registration
  - set_executor_policy(): Configure default execution strategy ("auto", "production", "stub")
  - EXECUTOR_POLICY: Current policy configuration

For custom executors, implement ExecutorProtocol and register via:
  ExecutorRegistry.register("my_executor", MyExecutor())
"""

# Executor policy controls whether the registry provides production-capable
# executors or lightweight stubs. Default is 'auto' to prefer production
# execution for sandboxed runs while keeping registry bindings deterministic.
EXECUTOR_POLICY = {"mode": "auto"}


def set_executor_policy(mode: str):
	if mode not in ("stub", "production", "auto"):
		raise UserInputError("unsupported executor policy mode")
	EXECUTOR_POLICY["mode"] = mode
	ExecutorRegistry.clear()
	if mode == "production":
		ExecutorRegistry.register("docker", ProductionDockerExecutor())
	else:
		ExecutorRegistry.register("docker", DockerExecutor())
	ExecutorRegistry.register("local", LocalExecutor())
	global EXECUTORS
	EXECUTORS = {name: ExecutorRegistry.get(name) for name in ExecutorRegistry.list()}


# create registry and pre-register allowed executors
ExecutorRegistry = _ExecutorRegistry()
set_executor_policy(EXECUTOR_POLICY["mode"])

__all__ = [
	"ExecutorRegistry",
	"set_executor_policy",
	"EXECUTOR_POLICY",
]
