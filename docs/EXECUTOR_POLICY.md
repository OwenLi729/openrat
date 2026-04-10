# Executor Policy

OpenRat keeps Docker-backed execution as the default, recommended, and safest
execution path. OpenRat also supports an explicit trusted-host-only local
execution mode for developer convenience and environments where Docker is unavailable.

Local execution is **not** a sandbox and is never used as an implicit fallback.

## Architecture

```
Openrat / OpenRatAgent
    └── _choose_executor()
        ├── Docker executor         ← default / recommended
        │       └── docker run --rm
        │               --network none
        │               --security-opt no-new-privileges
        │               --cap-drop ALL
        │               --read-only
        │               --tmpfs /tmp
        │               --pids-limit 100
        │               -u <uid>:<gid>
        │               --memory <limit>
        │               --cpus <limit>
        └── Local executor          ← explicit trusted-host opt-in only
            └── subprocess.run(...) with guardrails, timeout,
            and best-effort host resource limits
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

## Local executor properties

When `executor="local"` is explicitly selected:

| Property | Value |
|----------|-------|
| Container isolation | None |
| Network isolation | None |
| Command guardrails | Still enforced |
| Governance / autonomy | Still enforced |
| Patch policy | Still enforced |
| Tool capability enforcement | Still enforced |
| Timeout | Enforced |
| Resource limits | Best-effort host limits |

All local execution results include the warning:

> Local execution bypasses container sandboxing.

## Resource limits and timeout

Openrat enforces bounded execution limits by default for both executors:

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

Executors are internal runtime implementation details. Users select execution
mode through `Openrat` configuration or the CLI, not by importing executor
classes, registries, or policy helpers.

## Configuration

Pass `executor` and optional resource limits in the `Openrat` config dict:

```python
from openrat import Openrat

app = Openrat({
    "executor": "docker",          # default / recommended
    "docker_image": "python:3.11", # image to run scripts in
    "memory": "512m",              # bounded; max 4g unless allow_unbounded_limits=True
    "cpus": "1.0",                 # bounded; max 4.0 unless allow_unbounded_limits=True
    "timeout": 300,                 # bounded; max 3600 unless allow_unbounded_limits=True
})
```

To opt into trusted-host execution explicitly:

```python
app = Openrat({
    "executor": "local",
})
```

Use `local` only for trusted workflows, fast iteration, or environments without
Docker. Prefer Docker for untrusted, long-running, or reproducibility-sensitive
experiments.

## Internal registry

Openrat maintains an internal executor registry under the private runtime
namespace. It is not part of the public API and should not be imported by user
code.

## Executor result

Executors return a serializable result mapping. Docker results include:

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

Local results additionally include:

```python
{
    "executor": "local",
    "sandboxed": False,
    "security_error": "Local execution bypasses container sandboxing.",
    "resource_limits_applied": bool,
}
```
