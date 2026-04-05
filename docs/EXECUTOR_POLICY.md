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
                            --cap-drop ALL
                            --read-only
                            --tmpfs /tmp
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
| Linux capabilities | Dropped (`--cap-drop ALL`) |
| Root filesystem | Read-only (`--read-only`) |
| Temporary writable FS | `/tmp` tmpfs only (`--tmpfs /tmp`) |
| PID limit | 100 |
| User | Current UID/GID (non-root) |
| Filesystem | Ephemeral per-run temp directory; `/code` read-only, `/outputs` writable |
| Cleanup | Container removed immediately on exit (`--rm`) |

## Resource limits and timeout

Openrat enforces bounded execution limits by default:

| Control | Default | Maximum |
|---------|---------|---------|
| Timeout | 300s | 3600s |
| Memory  | 512m | 4g |
| CPUs    | 1.0 | 4.0 |

Unbounded execution is denied by default. It can only be enabled with explicit
user opt-in via config:

```python
app = Openrat({
    "executor": "docker",
    "allow_unbounded_limits": True,
})
```

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
    "memory": "512m",              # bounded; max 4g unless allow_unbounded_limits=True
    "cpus": "1.0",                 # bounded; max 4.0 unless allow_unbounded_limits=True
    "timeout": 300,                 # bounded; max 3600 unless allow_unbounded_limits=True
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
