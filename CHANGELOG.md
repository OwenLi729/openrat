# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

- No unreleased changes recorded yet.

## [0.1.0] - 2026-03-30

- Public API and workflow stabilization around `Openrat` facade.
- Governance/session refactoring and policy enforcement hardening.
- Executor cleanup and Docker-first execution path consolidation.
- Internal API cleanup and import path modernization.
- Documentation and examples updated to align with public API usage.
- Test suite status for release: `85 passed, 4 skipped`.

## [0.0.x] - 2026-03-05

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
