import sys
from pathlib import Path

# ensure project root is on sys.path when running tests directly
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from openrat.model._factory import ModelFactory
from openrat.model._agent_loop import AgentLoop
from openrat.model.types import Message


def test_agent_loop_with_factory_adapter():
    cfg = {"provider": "openai_compatible", "base_url": None, "api_key": None, "model_name": "gpt-test"}
    model = ModelFactory.create(cfg)
    loop = AgentLoop(model)

    resp = loop.run_once([Message(role="user", content="integrate me")])
    assert resp.content is not None
    assert "integrate me" in (resp.content or "")


