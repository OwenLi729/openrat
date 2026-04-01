"""LLM provider adapters and message types.

Internal module: Contains provider integrations (OpenAI, Claude, Gemini)
and message types. Users should not import directly from this module.

Public types are re-exported from the root package:
    from openrat import Message, ModelResponse

Provider configuration is handled via Openrat config dict:
    from openrat import Openrat
    
    app = Openrat({
        "provider": "openai_compatible",
        "api_key": "sk-...",
        "model_name": "gpt-4o",
    })
"""
