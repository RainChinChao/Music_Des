from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from typing import Any

from .music_schema import MUSIC_JSON_SCHEMA


def _extract_json(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0]
        if cleaned.lstrip().startswith("json"):
            cleaned = cleaned.lstrip()[4:].lstrip()
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start < 0 or end < start:
        raise ValueError("model response does not contain a JSON object")
    result = json.loads(cleaned[start:end + 1])
    if not isinstance(result, dict):
        raise ValueError("model response JSON root must be an object")
    return result


class MusicProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str) -> dict[str, Any]: ...

    def generate_structured(self, prompt: str, schema: dict[str, Any],
                            schema_name: str) -> dict[str, Any]:
        raise NotImplementedError("This provider does not support arbitrary structured output")


class OpenAIProvider(MusicProvider):
    def __init__(self, model: str = "gpt-5.6", api_key: str | None = None) -> None:
        self.model, self.api_key = model, api_key or os.getenv("OPENAI_API_KEY")

    def generate(self, prompt: str) -> dict[str, Any]:
        return self.generate_structured(prompt, MUSIC_JSON_SCHEMA, "music_composition")

    def generate_structured(self, prompt: str, schema: dict[str, Any],
                            schema_name: str) -> dict[str, Any]:
        from openai import OpenAI
        response = OpenAI(api_key=self.api_key).responses.create(
            model=self.model,
            instructions="You are a music arranger. Produce schema-valid JSON only.",
            input=prompt,
            text={"format": {"type": "json_schema", "name": schema_name,
                             "strict": True, "schema": schema}},
        )
        return _extract_json(response.output_text)


class GeminiProvider(MusicProvider):
    def __init__(self, model: str = "gemini-3.6-flash", api_key: str | None = None) -> None:
        self.model, self.api_key = model, api_key or os.getenv("GEMINI_API_KEY")

    def generate(self, prompt: str) -> dict[str, Any]:
        return self.generate_structured(prompt, MUSIC_JSON_SCHEMA, "music_composition")

    def generate_structured(self, prompt: str, schema: dict[str, Any],
                            schema_name: str) -> dict[str, Any]:
        from google import genai
        client = genai.Client(api_key=self.api_key)
        try:
            # Gemini 3.6 uses Google's newer Interactions API response format.
            # Sending this model through the legacy generateContent structured-
            # output fields may return only a generic 400 INVALID_ARGUMENT.
            if self.model.startswith("gemini-3.6"):
                from importlib.metadata import version
                sdk_version = version("google-genai")
                try:
                    sdk_major = int(sdk_version.split(".", 1)[0])
                except ValueError:
                    sdk_major = 0
                if sdk_major < 2:
                    raise RuntimeError(
                        f"Gemini 3.6 requires google-genai 2.x; installed version is "
                        f"{sdk_version}. Run: python -m pip uninstall -y google-genai && "
                        "python -m pip install -U 'google-genai>=2,<3'"
                    )
                try:
                    response = client.interactions.create(
                        model=self.model,
                        input=prompt,
                        response_format={
                            "type": "text", "mime_type": "application/json",
                            "schema": schema,
                        },
                    )
                except Exception as structured_exc:
                    structured_message = str(structured_exc)
                    if ("INVALID_ARGUMENT" not in structured_message and
                            "invalid argument" not in structured_message.lower() and
                            "invalid_request" not in structured_message.lower()):
                        raise
                    # Gemini rejects some large/deep schemas even though their
                    # individual keywords are supported. Retry without native
                    # schema enforcement, then parse and validate locally.
                    fallback_prompt = (
                        prompt + "\n\nGoogle native structured output rejected the schema. "
                        "Return exactly one JSON object, with no Markdown or commentary, "
                        "that follows this schema:\n" +
                        json.dumps(schema, ensure_ascii=False)
                    )
                    response = client.interactions.create(
                        model=self.model, input=fallback_prompt)
                text = response.output_text
            else:
                response = client.models.generate_content(
                    model=self.model, contents=prompt,
                    config={"response_mime_type": "application/json",
                            "response_json_schema": schema},
                )
                text = response.text
        except Exception as exc:
            message = str(exc)
            if "INVALID_ARGUMENT" in message or "invalid argument" in message.lower():
                raise RuntimeError(
                    f"Google rejected the structured-output request for `{self.model}`. "
                    "Confirm that this model is enabled for the Google AI Studio project and "
                    "upgrade the SDK with `python -m pip install -U 'google-genai>=2,<3'`. "
                    "The application tried both native structured output and the "
                    "JSON-only locally validated fallback. "
                    f"Original Google error: {message}"
                ) from exc
            raise
        return _extract_json(text)


class ClaudeProvider(MusicProvider):
    def __init__(self, model: str = "claude-sonnet-5", api_key: str | None = None) -> None:
        self.model, self.api_key = model, api_key or os.getenv("ANTHROPIC_API_KEY")

    def generate(self, prompt: str) -> dict[str, Any]:
        return self.generate_structured(prompt, MUSIC_JSON_SCHEMA, "music_composition")

    def generate_structured(self, prompt: str, schema: dict[str, Any],
                            schema_name: str) -> dict[str, Any]:
        import anthropic
        response = anthropic.Anthropic(api_key=self.api_key).messages.create(
            model=self.model, max_tokens=16000, temperature=0,
            system="Return one JSON object only. Follow the schema in the user prompt.",
            messages=[{"role": "user", "content": prompt + "\n\nRequired JSON schema:\n" +
                       json.dumps(schema, ensure_ascii=False)}],
        )
        text = "".join(block.text for block in response.content if hasattr(block, "text"))
        return _extract_json(text)


class OllamaProvider(MusicProvider):
    def __init__(self, model: str = "qwen2.5:7b-instruct",
                 base_url: str = "http://localhost:11434") -> None:
        self.model, self.base_url = model, base_url.rstrip("/")

    def generate(self, prompt: str) -> dict[str, Any]:
        return self.generate_structured(prompt, MUSIC_JSON_SCHEMA, "music_composition")

    def generate_structured(self, prompt: str, schema: dict[str, Any],
                            schema_name: str) -> dict[str, Any]:
        import requests
        from .system_setup import model_is_installed, ollama_tags
        names = ollama_tags(self.base_url)
        if not model_is_installed(self.model, names):
            raise RuntimeError(
                f"Ollama model `{self.model}` is not installed. Run `ollama pull {self.model}` "
                "or use `music-doctor --start-ollama --pull-model`."
            )
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={"model": self.model, "prompt": prompt, "stream": False,
                      "format": schema, "options": {"temperature": 0}},
                timeout=600,
            )
        except requests.ConnectionError as exc:
            raise RuntimeError(
                "Ollama stopped before generation. Run `brew services start ollama` "
                "or keep `ollama serve` running."
            ) from exc
        response.raise_for_status()
        return _extract_json(response.json()["response"])


class OpenAICompatibleProvider(MusicProvider):
    """Structured provider for OpenAI-compatible training/model gateways."""

    def __init__(self, model: str, api_key: str | None, base_url: str) -> None:
        self.model, self.api_key, self.base_url = model, api_key, base_url

    def generate(self, prompt: str) -> dict[str, Any]:
        return self.generate_structured(prompt, MUSIC_JSON_SCHEMA, "music_composition")

    def generate_structured(self, prompt: str, schema: dict[str, Any],
                            schema_name: str) -> dict[str, Any]:
        from openai import OpenAI
        schema_prompt = prompt + "\n\nReturn JSON only. Required schema:\n" + json.dumps(
            schema, ensure_ascii=False)
        response = OpenAI(api_key=self.api_key, base_url=self.base_url).chat.completions.create(
            model=self.model, temperature=0, max_tokens=16000,
            messages=[{"role": "user", "content": schema_prompt}],
        )
        return _extract_json(response.choices[0].message.content or "")


class DeepSeekProvider(OpenAICompatibleProvider):
    def __init__(self, model: str = "deepseek-v4-flash",
                 api_key: str | None = None) -> None:
        super().__init__(model, api_key or os.getenv("DEEPSEEK_API_KEY"),
                         "https://api.deepseek.com")


class OpenRouterProvider(OpenAICompatibleProvider):
    def __init__(self, model: str = "openrouter/free",
                 api_key: str | None = None) -> None:
        super().__init__(model, api_key or os.getenv("OPENROUTER_API_KEY"),
                         "https://openrouter.ai/api/v1")


def create_provider(name: str, model: str | None = None,
                    api_key: str | None = None) -> MusicProvider:
    key = name.strip().lower()
    classes = {"openai": OpenAIProvider, "gpt": OpenAIProvider,
               "gemini": GeminiProvider, "google-ai-studio": GeminiProvider,
               "aistudio": GeminiProvider, "claude": ClaudeProvider,
               "deepseek": DeepSeekProvider, "openrouter": OpenRouterProvider,
               "ollama": OllamaProvider, "local": OllamaProvider}
    if key not in classes:
        raise ValueError(f"unsupported provider: {name}")
    if key in {"ollama", "local"}:
        return classes[key](model=model) if model else classes[key]()
    kwargs = {"api_key": api_key}
    if model: kwargs["model"] = model
    return classes[key](**kwargs)
