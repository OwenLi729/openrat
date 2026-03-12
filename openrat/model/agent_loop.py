from typing import List, Optional

from .types import Message, ModelResponse, ToolCall

class AgentLoop:
    def __init__(self, adapter, tool_registry=None):
        self.adapter = adapter
        self.tool_registry = tool_registry

    def run_once(self, messages: List[Message]) -> ModelResponse:
        """One LLM call: generate a response and execute any tool calls."""
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

    def run(self, messages: List[Message], max_turns: int = 10) -> ModelResponse:
        """Drive the loop until the model stops calling tools or max_turns is reached.

        Tool results are appended to `messages` in-place so the model sees
        the full context on the next turn.
        """
        resp = None
        for _ in range(max_turns):
            resp = self.run_once(messages)
            if not resp.tool_calls:
                break
        return resp
