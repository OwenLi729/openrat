import sys
from pathlib import Path

# ensure project root is on sys.path when running tests directly
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from openrat.model.factory import ModelFactory
from openrat.model.types import Message


def test_factory_creates_adapters_and_generate():
    cfg_oai = {"provider": "openai_compatible", "base_url": None, "api_key": None, "model_name": "gpt-test"}
    m_oai = ModelFactory.create(cfg_oai)
    resp = m_oai.generate([Message(role="user", content="ping")])
    assert resp.raw and resp.raw.get("provider") == "openai_compatible"
    assert "ping" in (resp.content or "")

    cfg_claude = {"provider": "claude", "api_key": None, "model_name": "claude-test"}
    m_claude = ModelFactory.create(cfg_claude)
    resp2 = m_claude.generate([Message(role="user", content="hello")])
    assert "claude" in (resp2.content or "")

    cfg_gem = {"provider": "gemini", "api_key": None, "model_name": "gem-test"}
    m_gem = ModelFactory.create(cfg_gem)
    resp3 = m_gem.generate([Message(role="user", content="yo")])
    assert "gemini" in (resp3.content or "")
