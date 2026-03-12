"""Unit tests for openrat.tools.registry.ToolRegistry."""
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from openrat.tools.registry import ToolRegistry


def test_register_and_execute_happy_path():
    reg = ToolRegistry()
    reg.register("add", lambda args: {"result": args["a"] + args["b"]})
    result = reg.execute("add", {"a": 3, "b": 4})
    assert result == {"result": 7}


def test_execute_unknown_tool_raises_key_error():
    reg = ToolRegistry()
    with pytest.raises(KeyError, match="not found"):
        reg.execute("nonexistent", {})


def test_list_returns_registered_names():
    reg = ToolRegistry()
    reg.register("tool_a", lambda args: {})
    reg.register("tool_b", lambda args: {})
    names = reg.list()
    assert "tool_a" in names
    assert "tool_b" in names


def test_list_empty_on_fresh_registry():
    reg = ToolRegistry()
    assert reg.list() == []


def test_get_returns_callable():
    reg = ToolRegistry()
    fn = lambda args: {"ok": True}
    reg.register("my_tool", fn)
    assert reg.get("my_tool") is fn


def test_get_unknown_returns_none():
    reg = ToolRegistry()
    assert reg.get("missing") is None


def test_execute_passes_arguments_correctly():
    received = {}

    def capture(args):
        received.update(args)
        return {"captured": True}

    reg = ToolRegistry()
    reg.register("capture", capture)
    reg.execute("capture", {"key": "value", "num": 42})
    assert received == {"key": "value", "num": 42}


def test_register_overwrites_existing_tool():
    """Registering the same name twice should replace the first tool."""
    reg = ToolRegistry()
    reg.register("t", lambda args: {"v": 1})
    reg.register("t", lambda args: {"v": 2})
    assert reg.execute("t", {}) == {"v": 2}


def test_execute_propagates_tool_exception():
    def boom(args):
        raise RuntimeError("tool failed")

    reg = ToolRegistry()
    reg.register("boom", boom)
    with pytest.raises(RuntimeError, match="tool failed"):
        reg.execute("boom", {})
