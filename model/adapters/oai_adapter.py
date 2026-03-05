from typing import List, Optional

from typing import List, Optional, Dict, Any
import uuid
import requests
import json

from .base_adapter import BaseModelAdapter
from ..types import Message, ModelResponse, ToolCall


class OpenAICompatibleAdapter(BaseModelAdapter):
    provider = "openai_compatible"

    def __init__(self, base_url: Optional[str], api_key: Optional[str], model_name: Optional[str]):
        self.base_url = base_url
        self.api_key = api_key
        self.model_name = model_name

    def _parse_tool_calls(self, message_obj: Dict[str, Any]) -> List[ToolCall]:
        calls: List[ToolCall] = []

        # New-style explicit tool_calls array
        if isinstance(message_obj.get("tool_calls"), list):
            for tc in message_obj["tool_calls"]:
                func = tc.get("function", {})
                args = func.get("arguments")
                # arguments may be a JSON-encoded string
                try:
                    if isinstance(args, str):
                        args_parsed = json.loads(args)
                    else:
                        args_parsed = args or {}
                except Exception:
                    args_parsed = {}

                calls.append(ToolCall(id=tc.get("id", str(uuid.uuid4())), name=func.get("name"), arguments=args_parsed))

        # OpenAI function_call style
        elif isinstance(message_obj.get("function_call"), dict):
            fc = message_obj["function_call"]
            args = fc.get("arguments", "{}")
            try:
                args_parsed = json.loads(args) if isinstance(args, str) else (args or {})
            except Exception:
                args_parsed = {}

            calls.append(ToolCall(id=str(uuid.uuid4()), name=fc.get("name"), arguments=args_parsed))

        return calls

    def generate(self, messages: List[Message], tools: Optional[list] = None, config: Optional[dict] = None) -> ModelResponse:
        # If adapter is unconfigured, return a harmless stub response (no network)
        if not self.base_url or not self.api_key:
            last = messages[-1].content if messages else None
            return ModelResponse(content=f"[stub:{self.provider}] {last}" if last else None, tool_calls=[], raw={"provider": self.provider})

        payload = {
            "model": self.model_name,
            "messages": [m.__dict__ for m in messages],
            "tools": tools,
            "temperature": config.get("temperature", 0.2) if config else 0.2,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        resp = requests.post(f"{self.base_url}/chat/completions", json=payload, headers=headers, timeout=120)
        data = resp.json()

        choice = data.get("choices", [{}])[0]
        message = choice.get("message", {})

        tool_calls = self._parse_tool_calls(message)

        return ModelResponse(
            content=message.get("content"),
            tool_calls=tool_calls,
            stop_reason=choice.get("finish_reason"),
            raw=data,
        )