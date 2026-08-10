from unittest.mock import patch

from deterministic_midi.providers import (ClaudeProvider, DeepSeekProvider,
                                           GeminiProvider, OllamaProvider,
                                           OpenAIProvider, OpenRouterProvider,
                                           create_provider)


def test_online_provider_accepts_session_api_key_without_environment_write():
    with patch.dict("os.environ", {}, clear=True):
        provider = create_provider("openai", "test-model", api_key="session-secret")
        assert isinstance(provider, OpenAIProvider)
        assert provider.api_key == "session-secret"


def test_each_provider_factory_remains_backward_compatible():
    assert isinstance(create_provider("gemini", api_key="x"), GeminiProvider)
    assert isinstance(create_provider("claude", api_key="x"), ClaudeProvider)
    assert isinstance(create_provider("ollama", "qwen2.5:7b-instruct"), OllamaProvider)
    assert isinstance(create_provider("google-ai-studio", api_key="x"), GeminiProvider)
    assert isinstance(create_provider("deepseek", api_key="x"), DeepSeekProvider)
    assert isinstance(create_provider("openrouter", api_key="x"), OpenRouterProvider)


def test_gemini_36_uses_interactions_structured_output():
    with patch("google.genai.Client") as client_class:
        client_class.return_value.interactions.create.return_value.output_text = '{"ok": true}'
        result = GeminiProvider("gemini-3.6-flash", api_key="x").generate_structured(
            "prompt", {"type": "object", "properties": {"ok": {"type": "boolean"}}},
            "test_schema")
    assert result == {"ok": True}
    client_class.return_value.interactions.create.assert_called_once()
    request = client_class.return_value.interactions.create.call_args.kwargs
    assert request["response_format"]["type"] == "text"
    assert request["response_format"]["mime_type"] == "application/json"
    assert not isinstance(request["response_format"], list)
    client_class.return_value.models.generate_content.assert_not_called()


def test_earlier_gemini_models_keep_generate_content_compatibility():
    with patch("google.genai.Client") as client_class:
        client_class.return_value.models.generate_content.return_value.text = '{"ok": true}'
        result = GeminiProvider("gemini-3.5-flash", api_key="x").generate_structured(
            "prompt", {"type": "object"}, "test_schema")
    assert result == {"ok": True}
    client_class.return_value.models.generate_content.assert_called_once()


def test_gemini_36_rejects_legacy_sdk_before_api_call():
    with patch("google.genai.Client") as client_class, \
         patch("importlib.metadata.version", return_value="1.75.0"):
        try:
            GeminiProvider("gemini-3.6-flash", api_key="x").generate_structured(
                "prompt", {"type": "object"}, "test_schema")
        except RuntimeError as exc:
            assert "requires google-genai 2.x" in str(exc)
        else:
            raise AssertionError("legacy SDK should have been rejected")
    client_class.return_value.interactions.create.assert_not_called()


def test_gemini_36_retries_without_native_schema_when_google_rejects_complexity():
    rejected = RuntimeError("400 invalid_request: Request contains an invalid argument")
    successful = type("Response", (), {"output_text": '{"ok": true}'})()
    with patch("google.genai.Client") as client_class:
        create = client_class.return_value.interactions.create
        create.side_effect = [rejected, successful]
        result = GeminiProvider("gemini-3.6-flash", api_key="x").generate_structured(
            "prompt", {"type": "object", "properties": {"ok": {"type": "boolean"}}},
            "test_schema")
    assert result == {"ok": True}
    assert create.call_count == 2
    first, second = create.call_args_list
    assert "response_format" in first.kwargs
    assert "response_format" not in second.kwargs
    assert "Return exactly one JSON object" in second.kwargs["input"]
