from typing import List, Optional

from .types import Message, ModelResponse, ToolCall


class AgentLoop:
    def __init__(self, adapter, tool_registry=None):
        self.adapter = adapter
        self.tool_registry = tool_registry

    def run_once(self, messages: List[Message]) -> ModelResponse:
        resp: ModelResponse = self.adapter.generate(messages)

        # handle tool calls by delegating to registry and appending tool messages
        if resp.tool_calls and self.tool_registry:
            for tc in resp.tool_calls:
                try:
                    result = self.tool_registry.execute(tc.name, tc.arguments)
                except Exception as e:
                    result = {"status": "error", "error": str(e)}

                messages.append(Message(role="tool", content=str(result)))

        return resp
