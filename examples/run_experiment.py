"""
Example: Direct experiment execution.

Demonstrates the simplest Openrat use case: execute an experiment file
and capture the output.

Usage:
    python examples/run_experiment.py
"""

from openrat import Openrat

# ── Config ────────────────────────────────────────────────────────────────────
# All execution is routed through the Docker executor for security isolation.
app = Openrat({
    "executor": "docker",
    "docker_image": "python:3.11",
})

# ── Run ───────────────────────────────────────────────────────────────────────
# Direct execution (without planning or LLM)
result = app.run(
    "tests/units/sandbox/fixtures/hello.py",   # path relative to cwd
    timeout=30,
    isolate=True,   # copies script into a temp dir before executing
    memory="256m",
    cpus="0.5",
)

# ── Results ───────────────────────────────────────────────────────────────────
print("status     :", result["status"])
print("return_code:", result["return_code"])
print("stdout     :", result["stdout"].strip())
if result.get("stderr"):
    print("stderr     :", result["stderr"].strip())
if result.get("timed_out"):
    print("process timed out")
