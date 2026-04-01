from collections.abc import MutableSequence

from .types import Message, ModelResponse, ToolCall
from openrat.core.errors import UserInputError, InternalError
from openrat.core.protocols import ModelAdapterProtocol, ToolRegistryProtocol

class AgentLoop:
    def __init__(self, adapter: ModelAdapterProtocol, tool_registry: ToolRegistryProtocol | None = None):
        self.adapter = adapter
        self.tool_registry = tool_registry

    def run_once(self, messages: MutableSequence[Message]) -> ModelResponse:
        """One LLM call: generate a response and execute any tool calls."""
        resp: ModelResponse = self.adapter.generate(messages)
        if resp is None:
            raise InternalError("model adapter returned no response")

        # handle tool calls by delegating to registry and appending tool messages
        if resp.tool_calls and self.tool_registry:
            for tc in resp.tool_calls:
                try:
                    result = self.tool_registry.execute(tc.name, tc.arguments)
                except Exception as e:
                    result = {"status": "error", "error": str(e)}

                messages.append(Message(role="tool", content=str(result)))

        return resp

    def run(self, messages: MutableSequence[Message], max_turns: int = 10) -> ModelResponse:
        """Drive the loop until the model stops calling tools or max_turns is reached.

        Tool results are appended to `messages` in-place so the model sees
        the full context on the next turn.
        """
        if not isinstance(max_turns, int) or max_turns <= 0:
            raise UserInputError("max_turns must be a positive integer")

        resp: ModelResponse | None = None
        for _ in range(max_turns):
            resp = self.run_once(messages)
            if not resp.tool_calls:
                break
        if resp is None:
            raise InternalError("agent loop exited without producing a response")
        return resp
