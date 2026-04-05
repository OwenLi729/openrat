# OpenRat API Architecture

This document describes how the two main subsystems — the **execution runner** and
the **LLM agent loop** — fit together and how to use them.

`Openrat` is the recommended public API. `OpenRatAgent` remains public as a
low-level/legacy runtime adapter for backward compatibility.

---

## Conceptual overview

```
User code
   │
   ▼
Openrat (openrat/api/openrat.py)
   ├─── Framework workflow (recommended)
   │       create_session → spec_from_final_json → build_plan → execute_plan
   │       └── Plan/DAG execution + Artifact creation
   │
   ├─── Direct compatibility path (non-planned)
   │       app.run("experiment.py")
   │       └── OpenRatAgent.run(...)
    │               └── _choose_executor() → ProductionDockerExecutor
    │                       └── docker run (hardened flags)
   │
   └─── LLM agent loop compatibility path (requires model config)
       app.chat([Message(role="user", content="...")])
       └── OpenRatAgent.chat(...) → AgentLoop.run(messages)
           ├── adapter.generate(messages)   ← LLM call
           ├── if tool_calls → ToolRegistry.execute(name, args)
           │       └── registered tool (e.g. "run_experiment")
           │               └── openrat.api.runner.run(...)
           └── repeat until no more tool calls
```

---

## Two layers

### Layer 1 — Recommended facade + direct runner

`Openrat` owns session/spec/plan/artifact workflow. It also forwards
`run(path)` as a direct, LLM-free compatibility path.

```python
from openrat import Openrat

app = Openrat({"executor": "docker", "docker_image": "python:3.11"})
result = app.run("experiments/train.py", timeout=120)
print(result["stdout"])
```

Key components:

| Component | Location | Role |
|-----------|----------|------|
| `Openrat` | `openrat/api/openrat.py` | Recommended facade for framework workflow |
| `OpenRatAgent` | `openrat/api/runner.py` | Low-level runtime + LLM adapter |
| `_choose_executor` | `openrat/api/runner.py` | Selects hardened Docker executor |
| `ProductionDockerExecutor` | `openrat/executors/docker_executor.py` | Hardened Docker execution |
| `validate_command_guardrails` | `openrat/sandbox/guardrails.py` | Defense-in-depth command pattern blocking |

---

### Layer 2 — LLM agent loop

`Openrat.chat(messages)` forwards to `OpenRatAgent.chat(messages)` and drives a
**multi-turn LLM loop**. The model can call tools (e.g. run experiments) and the
loop continues until the model produces no more tool calls.

```python
from openrat import Openrat
from openrat.model.types import Message

app = Openrat({
    "provider": "openai_compatible",
    "base_url": "https://api.openai.com/v1",
    "api_key": "sk-...",
    "model_name": "gpt-4o",
})

response = app.chat([
    Message(role="user", content="Run experiments/train.py and summarise the output.")
])
print(response.content)
```

Key components:

| Component | Location | Role |
|-----------|----------|------|
| `ModelFactory` | `openrat/model/factory.py` | Creates provider adapter from config |
| `AgentLoop` | `openrat/model/agent_loop.py` | Drives multi-turn LLM + tool loop |
| `ToolRegistry` | `openrat/tools/registry.py` | Holds named tools callable by the model |
| Provider adapters | `openrat/model/adapters/` | OpenAI-compatible, Claude, Gemini |

When model config keys (`provider`, `api_key`, etc.) are present in the config dict
passed to `Openrat` (or directly to `OpenRatAgent`), the low-level runtime builds
an `AgentLoop` and registers the `run_experiment` tool so the model can invoke the
execution runner.

---

## Supported providers

| `provider` key | Adapter | Notes |
|----------------|---------|-------|
| `openai_compatible` | `OpenAICompatibleAdapter` | Works for OpenAI, local vLLM, LM Studio, etc. |
| `claude` | `ClaudeAdapter` | Anthropic Claude API |
| `gemini` | `GeminiAdapter` | Google Gemini API |

---

## Registering custom tools

```python
from openrat import Openrat

def my_tool(arguments: dict) -> dict:
    # do something
    return {"result": 42}

agent = Openrat({
    "provider": "openai_compatible",
    "autonomy": 3,
    "user_approvals": {"host.exec"},
    ...
})
agent.tool_registry.register("my_tool", my_tool, capability="host.exec")
```

Any registered tool callable will be invoked when the model emits a matching tool
call. It receives the raw `arguments` dict and must return a JSON-serialisable dict.

Untrusted callable tools require explicit `host.exec` capability and user opt-in.

---

## Executor policy

OpenRat uses Docker-only execution (production-hardened):

```python
from openrat.executors import set_executor_policy
set_executor_policy("production")   # always Docker
set_executor_policy("auto")         # alias of production
```

---

## Security notes

- Experiments are copied into an ephemeral per-run temp directory; the original
  workspace is not modified.
- Docker runs have `--network none`, `--security-opt no-new-privileges`,
    `--cap-drop=ALL`, `--read-only`, `--tmpfs /tmp`, `--pids-limit 100`, and
    bounded memory/CPU/timeout limits by default.
- Experiment paths are validated to be inside the current working directory.
