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
        # If unconfigured, return a simple stub
        if not self.api_key:
            last = messages[-1].content if messages else None
            return ModelResponse(content=f"[stub:claude] {last}" if last else None, tool_calls=[], raw={"provider": self.provider})

        payload = {"model": self.model_name, "messages": [m.__dict__ for m in messages]}
        resp = requests.post("https://claude.example/api", json=payload, headers={"Authorization": f"Bearer {self.api_key}"}, timeout=30)
        data = resp.json()

        content_items = data.get("content", [])
        text_parts = []
        calls: List[ToolCall] = []
        for item in content_items:
            t = item.get("type")
            if t == "text":
                text_parts.append(item.get("text", ""))
            elif t == "tool_use":
                calls.append(ToolCall(id=item.get("id"), name=item.get("name"), arguments=item.get("input", {})))

        return ModelResponse(content="".join(text_parts) if text_parts else None, tool_calls=calls, stop_reason=data.get("stop_reason"), raw=data)
