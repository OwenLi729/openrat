"""
Example: registering a custom tool.

Shows how to register a Python function as a tool callable by the LLM.
The model can call any registered tool by name via its tool-call mechanism.

Usage:
    OPENAI_API_KEY=sk-... python examples/custom_tool.py
"""

import os
from openrat import Openrat, Message

# ── Custom tool ───────────────────────────────────────────────────────────────
def read_metrics(arguments: dict) -> dict:
    """Fake metric store — replace with real DB/file reads."""
    metric = arguments.get("metric", "accuracy")
    store = {"accuracy": 0.94, "loss": 0.12, "f1": 0.91}
    value = store.get(metric)
    if value is None:
        return {"error": f"unknown metric '{metric}'", "available": list(store.keys())}
    return {"metric": metric, "value": value}


# ── Agent setup ───────────────────────────────────────────────────────────────
app = Openrat({
    "executor": "docker",
    "docker_image": "python:3.11",
    "provider": "openai_compatible",
    "base_url": "https://api.openai.com/v1",
    "api_key": os.environ.get("OPENAI_API_KEY", ""),
    "model_name": "gpt-4o",
    "autonomy": 3,
    "user_approvals": {"host.exec"},
})

# Register alongside the built-in run_experiment tool
app.tool_registry.register("read_metrics", read_metrics, capability="host.exec")

# ── Run ───────────────────────────────────────────────────────────────────────
response = app.chat(
    "What is the current accuracy metric? Then run tests/units/sandbox/fixtures/hello.py.",
    max_turns=6,
)

print(response.content)
