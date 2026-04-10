# Changelog

All notable changes to this project will be documented in this file.

## [0.1.0] - 2026-04-01

### Added
- First public release of Openrat.
- Session/spec/plan/artifact framework workflow API via `Openrat`.
- Compatibility execution path with Docker-first executor selection.
- Optional LLM agent loop and tool-calling support.
- CLI entry point: `openrat`.

## [0.1.1] - 2026-04-10

### Added
- Local execution for ease of testing and fast setup.
- Added direct execution artifact helper that records executor metadata and security notices.

### Changed
- Docker remains the default and recommended executor; local execution is explicit opt-in only.
- Direct and tool-driven execution now surface executor choice and local-safety notices in results/artifacts.
- Fixed API key hard-requirement for OpenAI compatible models.

### Security
- No Docker-to-local fallback is performed when Docker is unavailable.
- Governance, autonomy, patch policy, and tool capability enforcement remain unchanged for local execution.