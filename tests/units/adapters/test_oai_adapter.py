import json
import types

import pytest

from openrat.model._adapters.oai_adapter import OpenAICompatibleAdapter
from openrat.model.types import Message, ToolCall, ModelResponse


class DummyResp:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


def test_oai_adapter_parses_tool_calls(monkeypatch):
    # Craft a vendor-like response with tool_calls
    vendor = {
        "choices": [
            {
                "message": {
                    "content": "run this",
                    "tool_calls": [
                        {"id": "1", "function": {"name": "exec", "arguments": json.dumps({"cmd": "echo hi"})}}
                    ],
                },
                "finish_reason": "stop",
            }
        ]
    }

    def fake_post(url, json=None, headers=None, timeout=None):
        return DummyResp(vendor)

    monkeypatch.setattr("openrat.model._adapters.oai_adapter.requests.post", fake_post)

    adapter = OpenAICompatibleAdapter(base_url="https://api", api_key="key", model_name="m1")
    resp = adapter.generate([Message(role="user", content="please")])

    assert isinstance(resp, ModelResponse)
    assert resp.content == "run this"
    assert resp.stop_reason == "stop"
    assert len(resp.tool_calls) == 1
    call = resp.tool_calls[0]
    assert isinstance(call, ToolCall)
    assert call.name == "exec"
    assert call.arguments == {"cmd": "echo hi"}


def test_oai_adapter_allows_local_base_url_without_api_key(monkeypatch):
    captured = {}

    vendor = {
        "choices": [
            {
                "message": {
                    "content": "local ok",
                    "tool_calls": [],
                },
                "finish_reason": "stop",
            }
        ]
    }

    def fake_post(url, json=None, headers=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers or {}
        return DummyResp(vendor)

    monkeypatch.setattr("openrat.model._adapters.oai_adapter.requests.post", fake_post)

    adapter = OpenAICompatibleAdapter(base_url="http://localhost:11434/v1", api_key=None, model_name="qwen")
    resp = adapter.generate([Message(role="user", content="please")])

    assert resp.content == "local ok"
    assert captured["url"] == "http://localhost:11434/v1/chat/completions"
    assert "Authorization" not in captured["headers"]
