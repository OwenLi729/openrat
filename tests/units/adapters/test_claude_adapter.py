import types

import pytest

from model.adapters.claude_adapter import ClaudeAdapter
from model.types import Message, ToolCall, ModelResponse


class DummyResp:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


def test_claude_adapter_parses_tool_use(monkeypatch):
    vendor = {
        "content": [
            {"type": "text", "text": "done"},
            {"type": "tool_use", "id": "tc1", "name": "run", "input": {"cmd": "ls"}},
        ],
        "stop_reason": "stop",
    }

    def fake_post(url, json=None, headers=None, timeout=None):
        return DummyResp(vendor)

    monkeypatch.setattr("model.adapters.claude_adapter.requests.post", fake_post)

    adapter = ClaudeAdapter(api_key="k", model_name="c1")
    resp = adapter.generate([Message(role="user", content="go")])

    assert isinstance(resp, ModelResponse)
    assert resp.content == "done"
    assert resp.stop_reason == "stop"
    assert len(resp.tool_calls) == 1
    tc = resp.tool_calls[0]
    assert isinstance(tc, ToolCall)
    assert tc.name == "run"
    assert tc.arguments == {"cmd": "ls"}
