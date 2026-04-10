# openrat
Your personal AI lab rat

Openrat is a research‑first, privacy‑preserving experiment agent designed to run, debug, chain, schedule, and report computational experiments while you go about your day.

It is built for researchers and research institutions who want automation without losing control, reproducibility, or interpretability.


What Openrat does
* Runs experiments in Docker with sandboxed execution by default
* Supports explicit trusted-host local execution for fast iteration
* Diagnoses failures and reports actionable diagnostics
* Chains and branches experiments based on results
* Safely applies bounded, auditable changes (e.g. configs, hyperparameters)
* Generates diagnostic artifacts (summaries, diffs, metrics, plots)
* Cluster / remote execution (coming soon)
* Optional email notifications (coming soon)

Openrat is editor‑agnostic (VS Code, Neovim, any IDE) and shell‑based by design.

## Installation

Install from PyPI:

```bash
pip install openrat
```

For local development:

```bash
pip install -e .
```


Research‑first by design.
Openrat is not a generic AI coding agent.

* It does not rewrite large portions of your codebase
* It preserves research intent and reproducibility
* All actions are explicit, logged, and reversible
* A human remains in the loop whenever ambiguity or risk arises

For larger changes, Openrat proposes patches with explanations rather than applying them automatically.


Bounded autonomy (capability‑scoped)
Openrat uses graduated autonomy levels, enforced outside the model:

* Level 0 — Observe only: run, diagnose, report
* Level 1 — Parameter autonomy: modify configs and hyperparameters
* Level 2 — Runtime repair: apply minimal fixes for common runtime errors (with safeguards)
* Level 3 — Extended edits (opt‑in): larger patches within explicitly allowed scope

Openrat cannot increase its own autonomy. All permissions are user‑controlled and auditable.

Governance is configured via `Session`:

```python
from openrat import Openrat, Session, AutonomyLevel

# Allow only observation (run, diagnose)
session = Session(
    autonomy=AutonomyLevel.OBSERVE,
    patch_policy="disabled"
)

# Build and execute plan within governance constraints
app = Openrat({"executor": "docker", "docker_image": "python:3.11"})
plan = app.build_plan(spec, session)
artifact = app.execute_plan(plan)
```


Experiment chaining & branching
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
* Local models or local execution workflows remain on your machine
* No code, data, or experiments leave your machine unless you choose
* Remote control workflows (coming soon; see `ROADMAP.md`)
* Autonomy and permissions are enforced by policy, not by the model


## Development

Run tests:

```bash
pytest tests/ -q
```

Set executor policy to production (default is `auto`):

```bash
Pytesting with EXECUTOR_POLICY=production pytest tests/
```


## Usage Guide

### 1. Quick Execution (Simplest)

Run a script and capture output:

```python
from openrat import Openrat

app = Openrat({"executor": "docker", "docker_image": "python:3.11"})
result = app.run(
    "experiments/train.py",
    timeout=120,
    isolate=True,    # copies script to temp dir for safety
    memory="1g",
    cpus="2.0",
)

print(result["stdout"])
print(f"Exit code: {result['return_code']}")
```

See `examples/run_experiment.py` for a complete example.

Examples require Docker to be running.

For trusted local development without Docker, you may explicitly opt into local
execution:

```python
app = Openrat({"executor": "local"})
result = app.run("experiments/train.py", timeout=60)
```

Local execution bypasses container sandboxing and is intended only for trusted
workflows.

### 2. Framework Workflow (Recommended)

Build and execute an experiment plan with governance:

```python
from openrat import Openrat, Session, AutonomyLevel, ExperimentSpec

# Create a session (defines autonomy and governance)
session = Session(
    autonomy=AutonomyLevel.OBSERVE,
    patch_policy="disabled",
)

# Define your experiment
spec = ExperimentSpec(
    goals=["Train model", "Evaluate"],
    metrics=["accuracy"],
    tasks=[...],
)

# Build and execute plan
app = Openrat({"executor": "docker", "docker_image": "python:3.11"})
plan = app.build_plan(spec, session)
artifact = app.execute_plan(plan, session, tools={...})

# Access results
print(artifact.status)
print(artifact.governance_report())
```

### 3. LLM Agent Loop (Chat Interface)

Let a language model decide which experiments to run and interpret results:

```python
from openrat import Openrat, Message
import os

app = Openrat({
    "executor": "docker",
    "docker_image": "python:3.11",
    "provider": "openai_compatible",
    "base_url": "https://api.openai.com/v1",
    "api_key": os.environ["OPENAI_API_KEY"],
    "model_name": "gpt-4o",
})

# Chat with the model; it can call tools to run experiments
messages = [
    Message(role="system", content="You are a research assistant."),
    Message(role="user", content="Run experiments/train.py and summarize the results."),
]

response = app.chat(messages, max_turns=5)
print(response.content)
```

See `examples/chat_agent.py` for a complete example.

### 4. Custom Tools (Advanced)

Register custom functions that the LLM can call:

```python
from openrat import Openrat

def read_metrics(arguments: dict) -> dict:
    """Custom tool callable by the LLM."""
    metric = arguments.get("metric", "accuracy")
    # Implement your metric reading logic
    return {"metric": metric, "value": 0.95}

app = Openrat({
    "provider": "openai_compatible",
    "api_key": "...",
    "model_name": "...",
    "autonomy": 3,
    "user_approvals": {"host.exec"},
})

# Untrusted callable tools require explicit host.exec opt-in
app.tool_registry.register("read_metrics", read_metrics, capability="host.exec")

# Now the LLM can call this tool
response = app.chat("Check the accuracy metric for me.")
```

See `examples/custom_tool.py` for a complete example.

## Session & Governance

Every execution runs within a `Session` that defines:

- **Autonomy level** — what the agent can do (observe, modify params, apply fixes, edit code)
- **Patch policy** — whether patches are proposed (disabled) or auto-applied
- **Approval scope** — which capabilities require explicit approval

All governance decisions are logged in an immutable audit trail, captured in the final `Artifact`:

```python
artifact.governance_report()
# {
#   "session_id": "...",
#   "autonomy": 0,  # Level 0 = observe only
#   "used_capabilities": ["observe"],
#   "blocked_capabilities": [],
#   "patches_proposed": [],
#   "events": [...]  # Full audit trail
# }
```

## Executor policy

Docker remains the default and recommended execution backend. Internally,
Openrat runs scripts in an ephemeral container with `--network none`,
`--security-opt no-new-privileges`, `--cap-drop=ALL`, `--read-only`,
`--tmpfs /tmp`, `--pids-limit 100`, and bounded memory/CPU limits.

Openrat also supports explicit `executor="local"` for trusted-host execution.
That path keeps governance, autonomy checks, patch policy, tool capability
enforcement, timeouts, and best-effort resource limits, but it does **not**
provide container isolation.

Openrat is safe-by-default for execution limits:

- default timeout: `300s`
- max timeout: `3600s`
- default memory: `512m` (max `4g`)
- default CPU: `1.0` (max `4.0`)

Unbounded limits are blocked unless explicitly enabled by user config
(`allow_unbounded_limits=True`).

Executor selection is an internal runtime concern. Configure it through
`Openrat({...})`, the CLI, or the agent runtime rather than importing executor
objects directly.

CLI selection is also explicit:

```bash
openrat run experiments/train.py --executor docker
openrat run experiments/train.py --executor local
```

If Docker is unavailable and you requested Docker, Openrat fails explicitly. It
does not silently downgrade to local execution.

## Roadmap

Planned items for v0.2+ and v0.3 are tracked in `ROADMAP.md`.
