# LLM Agent Loop

This document explains how `Openrat.chat()` drives a multi-turn LLM loop with tool execution.

## Overview

The LLM loop executes as follows:

1. Send messages and available tools to the model
2. Model responds with:
   - Final text → return response
   - Tool calls → execute tools, append results, repeat
3. Stop when model finishes or max turns reached

---

## Enabling the loop

The loop is built automatically by the low-level runtime when a `provider` key
is present in config:

```python
from openrat import Openrat

app = Openrat({
    "provider": "openai_compatible",  # or "claude" or "gemini"
    "base_url": "https://api.openai.com/v1",
    "api_key": "sk-...",
    "model_name": "gpt-4o",
})
## Enabling the loop

Pass a model provider to `Openrat`:

```python
from openrat import Openrat

app = Openrat({
    "provider": "openai_compatible",  # or "claude" or "gemini"
    "api_key": "sk-...",
    "model_name": "gpt-4o",
})
```

Without a model provider, `app.chat()` will raise an error. Direct execution via `app.run()` works without a model
      Message(role="system", content="You are a research assistant."),
      Message(role="user",   content="Run experiments/train.py."),
  ])
  ```

The response is a `ModelResponse` dataclass:
```python
print(response.content)      # final text from the model
print(response.tool_calls)   # list of ToolCall (empty when loop finished cleanly)
print(response.stop_reason)  # e.g. "end_turn", "max_turns"
```

---

## Built-in tool: run_experiment

When a model provider is configured, `Openrat` automatically registers a
`run_experiment` tool. The model can call it with:

```json
{
  "name": "run_experiment",
  "arguments": {
    "path": "experiments/train.py",
    "timeout": 120,
    "memory": "1g",
    "cpus": "2.0"
  }
}
```

Arguments mirror `Openrat.run()` / `OpenRatAgent.run()`:

| Argument  | Type    | Default  | Description                             |
|-----------|---------|----------|-----------------------------------------|
| `path`    | string  | required | Path to experiment file (relative to cwd) |
| `timeout` | int     | None     | Max seconds before killing the process  |
| `isolate` | bool    | true     | Copy into ephemeral temp dir first      |
| `memory`  | string  | "512m"   | Docker memory limit                     |
| `cpus`    | string  | "1.0"    | Docker CPU limit                        |

---

## Registering custom tools

```python
from openrat import Openrat

app = Openrat({"provider": "openai_compatible", ...})

def fetch_metric(arguments: dict) -> dict:
    name = arguments["name"]
    # ... load from DB / file / API ...
    return {"metric": name, "value": 0.92}

app.tool_registry.register("fetch_metric", fetch_metric, capability="observe")

response = app.chat("Fetch accuracy and then run experiments/eval.py")
```

Any function `f(arguments: dict) -> dict` can be registered.

---

## max_turns

`app.chat(messages, max_turns=10)` limits the number of LLM calls to prevent
infinite loops. The loop exits early as soon as the model produces a response
with no tool calls. The final `ModelResponse` is always returned regardless of
how many turns were used.

---

## Using AgentLoop directly

If you want to manage the adapter and registry yourself:

```python
from openrat.model.factory import ModelFactory
from openrat.model.agent_loop import AgentLoop
from openrat.model.types import Message
from openrat.tools.registry import ToolRegistry

adapter = ModelFactory.create({
    "provider": "claude",
    "api_key": "sk-ant-...",
    "model_name": "claude-3-5-sonnet-20241022",
})

registry = ToolRegistry()
registry.register("my_tool", lambda args: {"result": 42})

loop = AgentLoop(adapter, tool_registry=registry)
resp = loop.run([Message(role="user", content="Use my_tool.")], max_turns=5)
print(resp.content)
```
