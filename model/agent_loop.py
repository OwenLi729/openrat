from typing import List

from .types import Message, ModelResponse, ToolCall


class AgentLoop:
    """Minimal agent loop used for testing.

    The loop consumes only the normalized `ModelResponse` contract and never
    touches provider-specific fields. It will process `tool_calls` if
    present, otherwise return the final content.
    """

    def __init__(self, model, tool_registry=None):
        self.model = model
        self.tool_registry = tool_registry

    def run_once(self, messages: List[Message]) -> ModelResponse:
        resp = self.model.generate(messages)

        # Only consume normalized fields
        if resp.tool_calls:
            # For tests we simply append tool results to messages when registry present
            if self.tool_registry:
                for call in resp.tool_calls:
                    result = self.tool_registry.execute(call.name, call.arguments)
                    messages.append(Message(role="tool", content=str(result)))

        return resp
