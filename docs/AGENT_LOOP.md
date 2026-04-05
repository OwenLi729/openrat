# LLM Agent Loop

This document explains how `Openrat.chat()` drives a multi-turn LLM loop with tool execution.

## Overview

The loop executes as follows:

1. Send messages to the model
2. Model responds with:
   - final text (loop exits), or
   - tool calls (tools execute, tool results are appended, loop continues)
3. Stop when tool calls end or `max_turns` is reached

## Enabling the loop

```python
from openrat import Openrat

app = Openrat({
    "provider": "openai_compatible",  # or "claude" / "gemini"
    "api_key": "sk-...",
    "model_name": "gpt-4o",
})
```

Without a model provider, `app.chat()` raises an error. `app.run()` still works.

## Built-in tool: `run_experiment`

When a model provider is configured, Openrat automatically registers `run_experiment`.
This built-in tool runs an experiment inside hardened Docker execution.

Arguments mirror `Openrat.run()`:

- `path` (required)
- `timeout` (default `300`, max `3600`)
- `isolate` (default `True`)
- `memory` (default `512m`, max `4g`)
- `cpus` (default `1.0`, max `4.0`)

## Custom tools and `host.exec`

Custom callable tools run in the host Python process. They are treated as untrusted by default.

Security requirements:

- custom callable tools must use capability `host.exec`
- session must explicitly opt in with `user_approvals={"host.exec"}`
- practical default is autonomy level `3` for `host.exec`

Example:

```python
from openrat import Openrat

app = Openrat({
    "provider": "openai_compatible",
    "api_key": "sk-...",
    "model_name": "gpt-4o",
    "autonomy": 3,
    "user_approvals": {"host.exec"},
})


def my_tool(arguments: dict) -> dict:
    return {"ok": True}

app.tool_registry.register("my_tool", my_tool, capability="host.exec")
```

## `max_turns`

`app.chat(messages, max_turns=10)` limits total model turns to prevent runaway loops.
