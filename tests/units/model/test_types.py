import sys
from pathlib import Path

# ensure project root is on sys.path when running tests directly
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from openrat.model.types import Message, ModelResponse, ToolCall


def test_message_and_response_dataclasses():
    m = Message(role="user", content="hello")
    assert m.role == "user"
    assert m.content == "hello"

    r = ModelResponse(content="ok", raw={"foo": "bar"})
    assert r.content == "ok"
    assert r.raw["foo"] == "bar"
    assert r.tool_calls == []
