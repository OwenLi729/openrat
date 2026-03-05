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
        # Unconfigured stub path
        if not self.api_key:
            last = messages[-1].content if messages else None
            return ModelResponse(content=f"[stub:{self.provider}] {last}" if last else None, tool_calls=[], raw={"provider": self.provider})

        payload = {"contents": [m.__dict__ for m in messages], "tools": tools}

        resp = requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={self.api_key}", json=payload, timeout=120)
        data = resp.json()

        tool_calls: List[ToolCall] = []
        content: Optional[str] = None

        candidates = data.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            for p in parts:
                if "text" in p:
                    content = p.get("text")

                if "functionCall" in p:
                    fc = p["functionCall"]
                    tool_calls.append(ToolCall(id=str(fc.get("id", "gemini_call")), name=fc.get("name"), arguments=fc.get("args", {})))

        stop_reason = candidates[0].get("finishReason") if candidates else None
        return ModelResponse(content=content, tool_calls=tool_calls, stop_reason=stop_reason, raw=data)