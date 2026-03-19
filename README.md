# openrat
Your personal AI lab rat

Openrat is a research‑first, privacy‑preserving experiment agent designed to run, debug, chain, schedule, and report computational experiments while you go about your day.

It is built for researchers and research institutions who want automation without losing control, reproducibility, or interpretability.


What Openrat does (coming soon)
* Runs experiments across local machines, clusters, Colab, and SSH
* Diagnoses failures and reports actionable diagnostics
* Chains and branches experiments based on results
* Safely applies bounded, auditable changes (e.g. configs, hyperparameters)
* Notifies you via email on completion, errors, or required input
* Generates diagnostic artifacts (summaries, diffs, metrics, plots)

Openrat is editor‑agnostic (VS Code, Neovim, any IDE) and shell‑based by design.


Research‑first by design
Openrat is not a generic AI coding agent.

* It does not rewrite large portions of your codebase
* It preserves research intent and reproducibility
* All actions are explicit, logged, and reversible
* A human remains in the loop whenever ambiguity or risk arises

For larger changes, Openrat proposes patches with explanations rather than applying them automatically.


Bounded autonomy (capability‑scoped) (coming soon)
Openrat uses graduated autonomy levels, enforced outside the model:

* Level 0 — Observe only: run, diagnose, report
* Level 1 — Parameter autonomy: modify configs and hyperparameters
* Level 2 — Runtime repair: apply minimal fixes for common runtime errors (with safeguards)
* Level 3 — Extended edits (opt‑in): larger patches within explicitly allowed scope

Openrat cannot increase its own autonomy. All permissions are user‑controlled and auditable.


Experiment chaining & branching (coming soon)
Openrat can:
* Run experiments sequentially or in parallel
* Branch based on metrics, failures, or diagnostics
* Modify parameters or select follow‑up experiments conditionally

Example:
Run experiment B only if validation loss improves after experiment A.
Chaining logic can be defined via natural language or structured instruction files (.yaml, .json, .md) for maximum reliability.


Model‑agnostic
* Supports local open‑source models or cloud models (GPT, Gemini)


Privacy & security
* Local runs
* No code, data, or experiments leave your machine unless you choose
* Optional email notifications and remote control are opt‑in and authenticated (coming soon)
* Autonomy and permissions are enforced by policy, not by the model


What Openrat is not
* ❌ A SaaS builder
* ❌ A fully autonomous coding agent

✅ It is a trustworthy research assistant that automates experiments while keeping you in control.


## API entry points

Use `Openrat` as the recommended public API.

```python
from openrat import Openrat

app = Openrat({"executor": "local"})

session = app.create_session(autonomy=..., patch_policy="interactive")
spec = app.spec_from_final_json(final_json)
plan = app.build_plan(spec, session)
artifact = app.execute_plan(plan, session, tools=my_tools)
```

`OpenRatAgent` remains public as a low-level/legacy API for direct execution and
direct LLM loop control. `Openrat.run()` and `Openrat.chat()` are compatibility
forwards for non-planned paths.


## Executor policy

Executor selection is configurable via a runtime policy. This allows tests and
deployments to control whether lightweight stubs or production-capable backends
are used.

- Default policy: `auto` — prefers production executors for sandboxed `docker`
  runs while keeping stub bindings for other paths.
- Other modes: `stub` (always use stub backends), `production` (register
  production-capable backends).

Example usage:

```python
from openrat.executors import set_executor_policy

# switch to production executors (useful in CI to exercise real paths)
set_executor_policy("production")

# or force stub bindings for fast unit tests
set_executor_policy("stub")
```

Note: the `EXECUTOR_POLICY` value is exported from the `executors` package and
can be inspected at runtime.
