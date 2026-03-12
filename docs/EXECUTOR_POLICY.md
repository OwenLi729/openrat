# Executor policy

This document explains the runtime executor policy introduced in the project.

Overview
--------

The `EXECUTOR_POLICY` controls which executor implementations are provided by
the `executors` package at runtime. This allows tests and CI to control
whether lightweight stubs or production-capable backends are used.

Modes
-----

- `auto` (default): prefer production executors for sandboxed `docker` runs
  while keeping stub bindings for other paths. This mode is useful in local
  development and CI to exercise the production path where appropriate.
- `stub`: always use stub backends (fast, deterministic unit tests).
- `production`: register production-capable backends for all executor types.

API
---

Use the following API from the `openrat.executors` package:

```python
from openrat.executors import set_executor_policy, EXECUTOR_POLICY

set_executor_policy("production")
print(EXECUTOR_POLICY)  # {'mode': 'production'}
```

Checking which executors are registered at runtime:

```python
from openrat.executors import _REGISTRY

print(_REGISTRY.list())  # ['docker', 'local']
```

Notes
-----

- The registry exposes `EXECUTORS` for backward compatibility; calling
  `set_executor_policy` will rebuild the registry bindings and refresh
  `EXECUTORS`.
- CI pipelines that should exercise production execution paths should call
  `set_executor_policy("production")` before running integration tests.
- The top-level `executors` module is a compatibility shim that re-exports
  from `openrat.executors`. All new code should import from `openrat.executors`.
