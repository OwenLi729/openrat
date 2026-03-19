"""
Example: LLM agent loop.

The app uses a language model to decide which experiments to run and
summarises the output. The model can call the built-in `run_experiment` tool
any number of times during the conversation.

Usage:
    OPENAI_API_KEY=sk-... python examples/chat_agent.py

Requires a valid API key for the configured provider.
"""

import os
from openrat import Openrat
from openrat.model.types import Message

# ── Config ────────────────────────────────────────────────────────────────────
app = Openrat({
    # Execution config
    "executor": "local",          # "docker" for hardened sandbox
    "docker_image": "python:3.11",

    # Model config — required to enable app.chat()
    "provider": "openai_compatible",
    "base_url": "https://api.openai.com/v1",
    "api_key": os.environ.get("OPENAI_API_KEY", ""),
    "model_name": "gpt-4o",
})

# ── Conversation ──────────────────────────────────────────────────────────────
messages = [
    Message(
        role="system",
        content=(
            "You are a research assistant. When asked to run experiments, "
            "use the run_experiment tool. Always summarise stdout in plain English."
        ),
    ),
    Message(
        role="user",
        content="Please run tests/units/sandbox/fixtures/hello.py and tell me what it printed.",
    ),
]

response = app.chat(messages, max_turns=5)

# ── Output ────────────────────────────────────────────────────────────────────
print(response.content)
