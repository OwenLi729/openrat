import pytest

from openrat.model.adapters.gemini_adapter import GeminiAdapter
from openrat.model.types import Message, ToolCall, ModelResponse


class DummyResp:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


def test_gemini_adapter_parses_function_call(monkeypatch):
    vendor = {
        "candidates": [
            {
                "content": {"parts": [{"text": "ok"}, {"functionCall": {"name": "run", "args": {"cmd": "whoami"}}}]},
                "finishReason": "stop",
            }
        ]
    }

    def fake_post(url, json=None, timeout=None):
        return DummyResp(vendor)

    monkeypatch.setattr("openrat.model.adapters.gemini_adapter.requests.post", fake_post)

    adapter = GeminiAdapter(api_key="k", model_name="g1")
    resp = adapter.generate([Message(role="user", content="start")])

    assert isinstance(resp, ModelResponse)
    assert resp.content == "ok"
    assert resp.stop_reason == "stop"
    assert len(resp.tool_calls) == 1
    tc = resp.tool_calls[0]
    assert isinstance(tc, ToolCall)
    assert tc.name == "run"
    assert tc.arguments == {"cmd": "whoami"}
