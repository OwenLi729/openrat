from typing import List, Optional, Dict, Any

import requests

from .base_adapter import BaseModelAdapter
from ..types import Message, ModelResponse, ToolCall


class ClaudeAdapter(BaseModelAdapter):
    provider = "claude"

    def __init__(self, api_key: Optional[str], model_name: Optional[str]):
        self.api_key = api_key
        self.model_name = model_name

    def generate(self, messages: List[Message], tools: Optional[list] = None, config: Optional[dict] = None) -> ModelResponse:
        # Unconfigured stub path
        if not self.api_key:
            last = messages[-1].content if messages else None
            return ModelResponse(content=f"[stub:{self.provider}] {last}" if last else None, tool_calls=[], raw={"provider": self.provider})

        payload = {
            "model": self.model_name,
            "max_tokens": 2048,
            "messages": [m.__dict__ for m in messages],
            "tools": tools,
        }

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        resp = requests.post("https://api.anthropic.com/v1/messages", json=payload, headers=headers, timeout=120)
        data = resp.json()

        content = None
        tool_calls: List[ToolCall] = []

        for block in data.get("content", []):
            if block.get("type") == "text":
                content = block.get("text")

            if block.get("type") == "tool_use":
                tool_calls.append(ToolCall(id=block.get("id"), name=block.get("name"), arguments=block.get("input", {})))

        return ModelResponse(content=content, tool_calls=tool_calls, stop_reason=data.get("stop_reason"), raw=data)