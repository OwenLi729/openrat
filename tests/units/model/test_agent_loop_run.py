"""
Unit tests for AgentLoop.run() — the multi-turn loop added on top of run_once().
"""
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from openrat.model.agent_loop import AgentLoop
from openrat.model.types import Message, ModelResponse, ToolCall
from openrat.tools.registry import ToolRegistry
from openrat.errors import UserInputError, InternalError


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_response(content="done", tool_calls=None):
    return ModelResponse(content=content, tool_calls=tool_calls or [])


class _AdapterNoTools:
    """Always returns a final response with no tool calls."""
    def __init__(self, content="finished"):
        self._content = content
        self.call_count = 0

    def generate(self, messages):
        self.call_count += 1
        return _make_response(content=self._content)


class _AdapterAlwaysTools:
    """Always requests a tool call — used to test max_turns cut-off."""
    def __init__(self):
        self.call_count = 0

    def generate(self, messages):
        self.call_count += 1
        return _make_response(tool_calls=[ToolCall(id="x", name="noop", arguments={})])


class _AdapterToolThenDone:
    """Returns a tool call on the first turn, then a final response."""
    def __init__(self):
        self.call_count = 0

    def generate(self, messages):
        self.call_count += 1
        if self.call_count == 1:
            return _make_response(
                content=None,
                tool_calls=[ToolCall(id="tc1", name="greet", arguments={"name": "world"})],
            )
        return _make_response(content="all done")


class _AdapterReturnsNone:
    def generate(self, messages):
        return None


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_run_exits_immediately_when_no_tool_calls():
    adapter = _AdapterNoTools("hello")
    loop = AgentLoop(adapter)
    messages = [Message(role="user", content="hi")]
    resp = loop.run(messages, max_turns=10)
    assert resp.content == "hello"
    assert adapter.call_count == 1


def test_run_stops_at_max_turns():
    adapter = _AdapterAlwaysTools()
    reg = ToolRegistry()
    reg.register("noop", lambda args: {"ok": True})
    loop = AgentLoop(adapter, tool_registry=reg)
    messages = [Message(role="user", content="go")]
    resp = loop.run(messages, max_turns=3)
    assert adapter.call_count == 3
    # last response still has tool_calls (loop didn't get a clean finish)
    assert len(resp.tool_calls) == 1


def test_run_two_turns_tool_then_done():
    adapter = _AdapterToolThenDone()
    reg = ToolRegistry()
    reg.register("greet", lambda args: {"greeting": f"hello {args['name']}"})
    loop = AgentLoop(adapter, tool_registry=reg)
    messages = [Message(role="user", content="start")]
    resp = loop.run(messages, max_turns=5)
    assert resp.content == "all done"
    assert adapter.call_count == 2
    # tool message should have been appended
    tool_msgs = [m for m in messages if m.role == "tool"]
    assert len(tool_msgs) == 1
    assert "hello world" in tool_msgs[0].content


def test_run_tool_error_appended_as_tool_message():
    adapter = _AdapterToolThenDone()
    reg = ToolRegistry()

    def failing_tool(args):
        raise ValueError("something went wrong")

    reg.register("greet", failing_tool)
    loop = AgentLoop(adapter, tool_registry=reg)
    messages = [Message(role="user", content="start")]
    resp = loop.run(messages, max_turns=5)
    tool_msgs = [m for m in messages if m.role == "tool"]
    assert len(tool_msgs) == 1
    assert "error" in tool_msgs[0].content.lower() or "something went wrong" in tool_msgs[0].content


def test_run_without_registry_ignores_tool_calls():
    """When no registry is provided, tool calls in response are ignored."""
    adapter = _AdapterAlwaysTools()
    loop = AgentLoop(adapter, tool_registry=None)
    messages = [Message(role="user", content="go")]
    # Without a registry, tool calls are never consumed — loop will exhaust max_turns
    resp = loop.run(messages, max_turns=2)
    assert adapter.call_count == 2
    # No tool messages should have been appended
    assert all(m.role != "tool" for m in messages)


def test_run_once_with_no_registry_returns_response():
    adapter = _AdapterNoTools("pong")
    loop = AgentLoop(adapter)
    resp = loop.run_once([Message(role="user", content="ping")])
    assert resp.content == "pong"
    assert resp.tool_calls == []


def test_run_returns_last_response():
    """run() must always return a ModelResponse, even when max_turns reached."""
    adapter = _AdapterAlwaysTools()
    reg = ToolRegistry()
    reg.register("noop", lambda args: {})
    loop = AgentLoop(adapter, tool_registry=reg)
    resp = loop.run([Message(role="user", content="x")], max_turns=1)
    assert isinstance(resp, ModelResponse)


def test_run_with_invalid_max_turns_raises_user_input_error():
    adapter = _AdapterNoTools("ok")
    loop = AgentLoop(adapter)
    with pytest.raises(UserInputError, match="max_turns"):
        loop.run([Message(role="user", content="x")], max_turns=0)


def test_run_once_with_none_response_raises_internal_error():
    loop = AgentLoop(_AdapterReturnsNone())
    with pytest.raises(InternalError, match="returned no response"):
        loop.run_once([Message(role="user", content="x")])
