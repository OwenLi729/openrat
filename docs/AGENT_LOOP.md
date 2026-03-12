# LLM Agent Loop

This document explains how `AgentLoop` and `OpenRatAgent.chat()` work together
to drive a multi-turn LLM loop.

---

## Overview

```
OpenRatAgent.chat(messages)
        │
        ▼
    AgentLoop.run(messages, max_turns=10)
        │
        ├── turn 1: adapter.generate(messages)
        │       ├── model returns text → done, return response
        │       └── model returns tool_calls
        │               └── ToolRegistry.execute(name, arguments)
        │                       └── registered tool function(arguments) → result
        │               └── append Message(role="tool", content=result) to messages
        │
        ├── turn 2: adapter.generate(messages)  ← model sees tool result
        │       └── ... repeat ...
        │
        └── stop when no tool_calls OR max_turns reached
```

---

## Enabling the loop

The loop is built automatically inside `OpenRatAgent` when a `provider` key is
present in config:

```python
from openrat import OpenRatAgent

agent = OpenRatAgent({
    "provider": "openai_compatible",  # or "claude" or "gemini"
    "base_url": "https://api.openai.com/v1",
    "api_key": "sk-...",
    "model_name": "gpt-4o",
})
```

Without `provider`, `agent.run(path)` (direct execution) still works but
`agent.chat()` will raise `RuntimeError`.

---

## Sending messages

`agent.chat()` accepts:

- A plain string (converted to `Message(role="user", content=...)`):
  ```python
  response = agent.chat("Run experiments/train.py and summarise the output.")
  ```
- A list of `Message` objects (for multi-turn context):
  ```python
  from openrat.model.types import Message

  response = agent.chat([
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

When a model provider is configured, OpenRatAgent automatically registers a
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

Arguments mirror `OpenRatAgent.run()`:

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
from openrat import OpenRatAgent

agent = OpenRatAgent({"provider": "openai_compatible", ...})

def fetch_metric(arguments: dict) -> dict:
    name = arguments["name"]
    # ... load from DB / file / API ...
    return {"metric": name, "value": 0.92}

agent.tool_registry.register("fetch_metric", fetch_metric)

response = agent.chat("Fetch accuracy and then run experiments/eval.py")
```

Any function `f(arguments: dict) -> dict` can be registered.

---

## max_turns

`agent.chat(messages, max_turns=10)` limits the number of LLM calls to prevent
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
