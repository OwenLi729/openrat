"""
Example: direct experiment execution (no LLM).

Uses the recommended Openrat facade. `run()` here is the direct, non-planned
compatibility path forwarded to the low-level runtime.

Usage:
    python examples/run_experiment.py
"""

from openrat import Openrat

# ── Config ────────────────────────────────────────────────────────────────────
# "executor" can be "docker", "local", or omitted (auto-detects Docker).
# "docker_image" is only used when the Docker executor is selected.
app = Openrat({
    "executor": "local",          # change to "docker" for sandboxed runs
    "docker_image": "python:3.11",
})

# ── Run ───────────────────────────────────────────────────────────────────────
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
