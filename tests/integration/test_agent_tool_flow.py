from openrat.model.agent_loop import AgentLoop
from openrat.model.types import Message, ToolCall, ModelResponse


class FakeAdapter:
    def generate(self, messages):
        # Returns a response that requests a tool call
        return ModelResponse(
            content="please run",
            tool_calls=[ToolCall(id="tc1", name="dummy", arguments={"cmd": "echo hi"})],
            stop_reason=None,
            raw={"mock": True},
        )


class FakeRegistry:
    def execute(self, name, args):
        # Simulate executing the tool and return a structured result
        return {"status": "ok", "tool": name, "args": args}


def test_agent_loop_handles_tool_calls_and_appends_message():
    adapter = FakeAdapter()
    registry = FakeRegistry()
    loop = AgentLoop(adapter, tool_registry=registry)

    messages = [Message(role="user", content="start")] 

    resp = loop.run_once(messages)

    # Response should be the adapter's ModelResponse
    assert isinstance(resp, ModelResponse)
    assert len(resp.tool_calls) == 1

    # AgentLoop should have appended a tool message when registry provided
    assert messages[-1].role == "tool"
    assert "ok" in messages[-1].content
