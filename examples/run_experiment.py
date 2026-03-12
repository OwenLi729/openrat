"""
Example: direct experiment execution (no LLM).

Runs a Python script via the configured executor (Docker if available,
otherwise local subprocess) and prints the captured output.

Usage:
    python examples/run_experiment.py
"""

from openrat import OpenRatAgent

# ── Config ────────────────────────────────────────────────────────────────────
# "executor" can be "docker", "local", or omitted (auto-detects Docker).
# "docker_image" is only used when the Docker executor is selected.
agent = OpenRatAgent({
    "executor": "local",          # change to "docker" for sandboxed runs
    "docker_image": "python:3.11",
})

# ── Run ───────────────────────────────────────────────────────────────────────
result = agent.run(
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
    print("⚠️  process timed out")
