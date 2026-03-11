from typing import List, Optional, Dict, Any
import requests

from .base_adapter import BaseModelAdapter
from ..types import Message, ModelResponse, ToolCall


class GeminiAdapter(BaseModelAdapter):
    provider = "gemini"

    def __init__(self, api_key: Optional[str], model_name: Optional[str]):
        self.api_key = api_key
        self.model_name = model_name

    def generate(self, messages: List[Message], tools: Optional[list] = None, config: Optional[dict] = None) -> ModelResponse:
        if not self.api_key:
            last = messages[-1].content if messages else None
            return ModelResponse(content=f"[stub:gemini] {last}" if last else None, tool_calls=[], raw={"provider": self.provider})

        payload = {"model": self.model_name, "messages": [m.__dict__ for m in messages]}
        # tests monkeypatch requests.post with a signature (url, json=None, timeout=None)
        resp = requests.post("https://gemini.example/api", json=payload, timeout=30)
        data = resp.json()

        candidates = data.get("candidates", [])
        if not candidates:
            return ModelResponse(content=None, tool_calls=[], raw=data)

        first = candidates[0]
        parts = first.get("content", {}).get("parts", [])
        text_parts = []
        calls: List[ToolCall] = []

        for p in parts:
            if "text" in p:
                text_parts.append(p.get("text"))
            if "functionCall" in p:
                fc = p.get("functionCall", {})
                calls.append(ToolCall(id=str(len(calls)), name=fc.get("name"), arguments=fc.get("args", {})))

        return ModelResponse(content="".join(text_parts) if text_parts else None, tool_calls=calls, stop_reason=first.get("finishReason"), raw=data)
