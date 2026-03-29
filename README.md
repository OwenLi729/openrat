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


Research‑first by design.
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


## Development

Run tests:

```bash
pytest tests/ -q
```

Set executor policy to production (default is `auto`):

```bash
Pytesting with EXECUTOR_POLICY=production pytest tests/
```


## Framework Workflow

`Openrat` is the recommended API for all use cases:

```python
from openrat import Openrat, ExperimentSpec, Session

# Create a session (defines autonomy and governance)
session = Session(autonomy_level=0)

# Define your experiment
spec = ExperimentSpec(
    goals=["Train model", "Evaluate"],
    metrics=["accuracy"],
    tasks=[...],
)

# Create the framework instance
app = Openrat({"executor": "docker", "docker_image": "python:3.11"})

# Build a plan (with policy approval checks)
plan = app.build_plan(spec, session)

# Execute the plan
artifact = app.execute_plan(plan, session)
```

**For LLM-driven workflows:**

```python
# Configure with a model provider
app = Openrat({
    "executor": "docker",
    "docker_image": "python:3.11",
    "provider": "openai_compatible",
    "api_key": "sk-...",
    "model_name": "gpt-4o",
})

# Chat with the model (enables tool calls to run experiments)
response = app.chat("Run experiments/train.py and summarize results")
```


## Executor policy

All execution is routed through the `DockerExecutor`, which runs scripts in an
ephemeral container with `--network none`, `--security-opt no-new-privileges`,
`--pids-limit 100`, and configurable memory/CPU limits. There is no local or
stub execution path in production.

```python
from openrat.executors import set_executor_policy

# Both modes register the DockerExecutor (the only available backend)
set_executor_policy("production")   # explicit
set_executor_policy("auto")          # default
```
