from .docker_executor import ProductionDockerExecutor, DockerExecutor
from .local_executor import LocalExecutor
from .registry import ExecutorRegistry

# Executor policy controls whether the registry provides production-capable
# executors or lightweight stubs. Default is 'auto' to prefer production
# execution for sandboxed runs while keeping registry bindings deterministic.
EXECUTOR_POLICY = {"mode": "auto"}


def set_executor_policy(mode: str):
	if mode not in ("stub", "production", "auto"):
		raise ValueError("unsupported executor policy mode")
	EXECUTOR_POLICY["mode"] = mode
	_REGISTRY.clear()
	if mode == "production":
		_REGISTRY.register("docker", ProductionDockerExecutor())
	else:
		_REGISTRY.register("docker", DockerExecutor())
	_REGISTRY.register("local", LocalExecutor())
	global EXECUTORS
	EXECUTORS = {name: _REGISTRY.get(name) for name in _REGISTRY.list()}


# create registry and pre-register allowed executors
_REGISTRY = ExecutorRegistry()
set_executor_policy(EXECUTOR_POLICY["mode"])

# backward-compatible mapping
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
