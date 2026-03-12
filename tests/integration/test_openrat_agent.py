"""
Integration tests for OpenRatAgent — chat(), run(), built-in tool, custom tools,
validate_experiment_path, and loop wiring.
"""
import sys
import os
import tempfile
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from openrat.api.runner import OpenRatAgent, _validate_experiment_path
from openrat.model.types import Message, ModelResponse, ToolCall
from openrat.tools.registry import ToolRegistry


# ── Helpers ───────────────────────────────────────────────────────────────────

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "units" / "sandbox" / "fixtures"


class _FakeAdapterFinal:
    """Immediately returns a final response with no tool calls."""
    def __init__(self, content="stub response"):
        self._content = content
        self.calls = []

    def generate(self, messages):
        self.calls.append([m.content for m in messages])
        return ModelResponse(content=self._content, tool_calls=[])


class _FakeAdapterRunsTool:
    """First turn: requests run_experiment; second turn: final answer."""
    def __init__(self, experiment_path):
        self._path = experiment_path
        self.call_count = 0

    def generate(self, messages):
        self.call_count += 1
        if self.call_count == 1:
            return ModelResponse(
                content=None,
                tool_calls=[
                    ToolCall(
                        id="tc1",
                        name="run_experiment",
                        arguments={"path": self._path},
                    )
                ],
            )
        return ModelResponse(content="experiment complete", tool_calls=[])


# ── chat() — basic ─────────────────────────────────────────────────────────────

def test_chat_without_provider_raises():
    agent = OpenRatAgent({"executor": "local"})
    with pytest.raises(RuntimeError, match="No model configured"):
        agent.chat("hello")


def test_chat_with_string_message(monkeypatch):
    adapter = _FakeAdapterFinal("ok")
    agent = OpenRatAgent({"provider": "openai_compatible", "api_key": None, "model_name": "x"})
    agent.agent_loop.adapter = adapter
    resp = agent.chat("ping")
    assert resp.content == "ok"
    assert len(adapter.calls) == 1
    assert adapter.calls[0][0] == "ping"


def test_chat_with_message_list(monkeypatch):
    adapter = _FakeAdapterFinal("reply")
    agent = OpenRatAgent({"provider": "openai_compatible", "api_key": None, "model_name": "x"})
    agent.agent_loop.adapter = adapter
    msgs = [
        Message(role="system", content="you are helpful"),
        Message(role="user",   content="do something"),
    ]
    resp = agent.chat(msgs)
    assert resp.content == "reply"


def test_chat_preserves_message_order(monkeypatch):
    """Messages passed to the adapter should be in the original order."""
    adapter = _FakeAdapterFinal()
    agent = OpenRatAgent({"provider": "openai_compatible", "api_key": None, "model_name": "x"})
    agent.agent_loop.adapter = adapter
    msgs = [
        Message(role="system", content="sys"),
        Message(role="user",   content="usr"),
    ]
    agent.chat(msgs)
    assert adapter.calls[0] == ["sys", "usr"]


# ── agent_loop wiring ──────────────────────────────────────────────────────────

def test_agent_loop_is_none_without_provider():
    agent = OpenRatAgent({"executor": "local"})
    assert agent.agent_loop is None


def test_agent_loop_built_with_provider():
    agent = OpenRatAgent({"provider": "claude", "api_key": None, "model_name": "x"})
    assert agent.agent_loop is not None
    assert agent.tool_registry is not None


# ── built-in run_experiment tool ───────────────────────────────────────────────

def test_run_experiment_tool_is_registered():
    agent = OpenRatAgent({"provider": "openai_compatible", "api_key": None, "model_name": "x"})
    assert "run_experiment" in agent.tool_registry.list()


def test_run_experiment_tool_returns_error_without_path():
    agent = OpenRatAgent({"provider": "openai_compatible", "api_key": None, "model_name": "x"})
    result = agent.tool_registry.execute("run_experiment", {})
    assert result["status"] == "error"
    assert "path" in result["reason"]


def test_run_experiment_tool_actually_runs_script(monkeypatch):
    """run_experiment tool calls agent.run() which calls the executor."""
    class DummyResult:
        return_code = 0
        stdout = "hello world"
        stderr = ""
        timed_out = False
        start_time = 0.0
        end_time = 0.1

        @property
        def succeeded(self): return True

    monkeypatch.setattr("openrat.executors.local_executor.run_command", lambda *a, **kw: DummyResult())

    agent = OpenRatAgent({"provider": "openai_compatible", "api_key": None, "model_name": "x", "executor": "local"})
    result = agent.tool_registry.execute(
        "run_experiment",
        {"path": str(FIXTURES_DIR / "hello.py")},
    )
    assert result["status"] == "completed"
    assert result["return_code"] == 0


# ── custom tool registration ───────────────────────────────────────────────────

def test_custom_tool_registered_and_callable():
    agent = OpenRatAgent({"provider": "openai_compatible", "api_key": None, "model_name": "x"})

    def greet(args):
        return {"greeting": f"hello {args['name']}"}

    agent.tool_registry.register("greet", greet)
    result = agent.tool_registry.execute("greet", {"name": "openrat"})
    assert result == {"greeting": "hello openrat"}


def test_chat_loop_invokes_custom_tool(monkeypatch):
    """Full loop: adapter requests custom tool → tool executes → adapter finishes."""
    calls = []

    def my_tool(args):
        calls.append(args)
        return {"value": 99}

    class _AdapterCallsTool:
        def __init__(self):
            self.n = 0

        def generate(self, messages):
            self.n += 1
            if self.n == 1:
                return ModelResponse(
                    content=None,
                    tool_calls=[ToolCall(id="t1", name="my_tool", arguments={"x": 1})],
                )
            return ModelResponse(content="done", tool_calls=[])

    agent = OpenRatAgent({"provider": "openai_compatible", "api_key": None, "model_name": "x"})
    agent.tool_registry.register("my_tool", my_tool)
    agent.agent_loop.adapter = _AdapterCallsTool()

    resp = agent.chat("go")
    assert resp.content == "done"
    assert calls == [{"x": 1}]


# ── multi-turn loop drives run_experiment ──────────────────────────────────────

def test_chat_drives_run_experiment_tool(monkeypatch):
    class DummyExecResult:
        return_code = 0
        stdout = "hello world\n"
        stderr = ""
        timed_out = False
        start_time = 0.0
        end_time = 0.2

        @property
        def succeeded(self): return True

    monkeypatch.setattr("openrat.executors.local_executor.run_command", lambda *a, **kw: DummyExecResult())

    experiment_path = str(FIXTURES_DIR / "hello.py")
    adapter = _FakeAdapterRunsTool(experiment_path)

    agent = OpenRatAgent({
        "provider": "openai_compatible",
        "api_key": None,
        "model_name": "x",
        "executor": "local",
    })
    agent.agent_loop.adapter = adapter

    resp = agent.chat("run the experiment", max_turns=5)
    assert resp.content == "experiment complete"
    assert adapter.call_count == 2


# ── _validate_experiment_path ──────────────────────────────────────────────────

def test_validate_path_file_not_found():
    with pytest.raises(FileNotFoundError):
        _validate_experiment_path("/tmp/does_not_exist_openrat_test.py")


def test_validate_path_outside_cwd_raises():
    # /tmp is outside the current working directory
    with tempfile.NamedTemporaryFile(suffix=".py", dir="/tmp", delete=False) as f:
        fpath = f.name
    try:
        with pytest.raises(PermissionError, match="current working directory"):
            _validate_experiment_path(fpath)
    finally:
        os.unlink(fpath)


def test_validate_path_inside_cwd_returns_resolved():
    # Use a real fixture file that lives inside the repo (cwd)
    p = _validate_experiment_path(str(FIXTURES_DIR / "hello.py"))
    assert p.is_absolute()
    assert p.exists()


# ── OpenRatAgent.run() direct execution ────────────────────────────────────────

def test_direct_run_returns_completed(monkeypatch):
    class DummyResult:
        return_code = 0
        stdout = "hello world\n"
        stderr = ""
        timed_out = False
        start_time = 0.0
        end_time = 0.1

        @property
        def succeeded(self): return True

    monkeypatch.setattr("openrat.executors.local_executor.run_command", lambda *a, **kw: DummyResult())
    agent = OpenRatAgent({"executor": "local"})
    result = agent.run(str(FIXTURES_DIR / "hello.py"), isolate=True)
    assert result["status"] == "completed"
    assert result["return_code"] == 0
