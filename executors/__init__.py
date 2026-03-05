"""Executors package

Expose a registry `EXECUTORS` mapping executor_type -> executor instance.
"""
from .docker_executor import ProductionDockerExecutor, DockerExecutor
from .local_executor import LocalExecutor
from .registry import ExecutorRegistry

# Executor policy controls whether the registry provides production-capable
# executors or lightweight stubs. Call `set_executor_policy("production")`
# to switch to production executors at runtime (useful for integration tests
# or deployment). Default is 'auto' to prefer production execution for
# sandboxed runs while keeping registry bindings deterministic.
EXECUTOR_POLICY = {"mode": "auto"}


def set_executor_policy(mode: str):
	"""Set executor policy mode. Supported: 'stub', 'production'.

	When set to 'production', the registry will register production-capable
	executors (e.g., `ProductionDockerExecutor`) for execution paths.
	"""
	if mode not in ("stub", "production", "auto"):
		raise ValueError("unsupported executor policy mode")
	EXECUTOR_POLICY["mode"] = mode
	# rebuild registry bindings according to policy
	_REGISTRY.clear()
	if mode == "production":
		_REGISTRY.register("docker", ProductionDockerExecutor())
	else:
		_REGISTRY.register("docker", DockerExecutor())
	_REGISTRY.register("local", LocalExecutor())
	# refresh backward-compatible mapping
	global EXECUTORS
	EXECUTORS = {name: _REGISTRY.get(name) for name in _REGISTRY.list()}


# create a registry and pre-register allowed executors at startup
_REGISTRY = ExecutorRegistry()
set_executor_policy(EXECUTOR_POLICY["mode"])

# backward-compatible mapping used by existing tests and code
EXECUTORS = {name: _REGISTRY.get(name) for name in _REGISTRY.list()}

__all__ = [
	"_REGISTRY",
	"EXECUTORS",
	"DockerExecutor",
	"ProductionDockerExecutor",
	"LocalExecutor",
	"set_executor_policy",
	"EXECUTOR_POLICY",
]
