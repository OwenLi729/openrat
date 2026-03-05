# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased] - 2026-03-05

- Added executor policy API to control which executor backends are used:
  - `executors.EXECUTOR_POLICY` (modes: `stub`, `production`, `auto`).
  - `executors.set_executor_policy(mode)` to switch modes at runtime.
- Added `ExecutorRegistry.clear()` to allow rebuilding registry bindings.
- Simplified `DockerExecutor` to a pure scheduling stub; `ProductionDockerExecutor`
  contains the real execution logic.
- `tools.executor` now respects the executor policy and supports `auto` mode,
  which prefers production execution for sandboxed `docker` runs.
- Improved payload validation in `tools/executor.py`: `cwd` is validated
  first; `timeout` is optional but validated when present.
- Fixed tests and normalization for model adapters; added adapter unit tests.

All tests pass locally: `20 passed` (run on 2026-03-05).
