# Executor Policy

OpenRat routes all execution through a single, hardened **`DockerExecutor`**.
There is no local or stub execution path in production.

## Architecture

```
Openrat / OpenRatAgent
    └── _choose_executor()
            └── DockerExecutor          ← the only registered backend
                    └── docker run --rm
                            --network none
                            --security-opt no-new-privileges
                            --pids-limit 100
                            -u <uid>:<gid>
                            --memory <limit>
                            --cpus <limit>
```

## Security properties

| Property | Value |
|----------|-------|
| Network | None (`--network none`) |
| Privilege escalation | Blocked (`--security-opt no-new-privileges`) |
| PID limit | 100 |
| User | Current UID/GID (non-root) |
| Filesystem | Ephemeral per-run temp directory; workspace not modified |
| Cleanup | Container removed immediately on exit (`--rm`) |

## Runtime API

Both modes below resolve to the same `DockerExecutor`:

```python
from openrat.executors import set_executor_policy

set_executor_policy("production")   # explicit
set_executor_policy("auto")          # default
```

Calling `set_executor_policy("stub")` or any other unknown mode raises a
`ValueError`.

## Configuration

Pass `executor` and optional resource limits in the `Openrat` config dict:

```python
from openrat import Openrat

app = Openrat({
    "executor": "docker",          # required
    "docker_image": "python:3.11", # image to run scripts in
    "memory": "512m",              # optional — passed to --memory
    "cpus": "1.0",                 # optional — passed to --cpus
})
```

## Registry

The `ExecutorRegistry` is keyed by executor name. Only `"docker"` is registered:

```python
from openrat.executors.registry import ExecutorRegistry

ExecutorRegistry.list()   # ["docker"]
executor = ExecutorRegistry.get("docker")
```

## Executor result

`DockerExecutor.execute()` returns:

```python
{
    "status": "completed" | "failed",
    "executor": "docker",
    "return_code": int,
    "stdout": str,
    "stderr": str,
    "timed_out": bool,
    "duration": float,   # seconds
}
```
