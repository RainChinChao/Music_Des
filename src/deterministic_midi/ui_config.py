from __future__ import annotations

PROVIDER_LABELS = [
    "Ollama (local)", "Google AI Studio (Gemini free tier)", "OpenAI GPT",
    "Gemini", "Claude", "DeepSeek API", "OpenRouter",
]

PROVIDER_KEYS = {
    "Ollama (local)": "ollama",
    "Google AI Studio (Gemini free tier)": "google-ai-studio",
    "OpenAI GPT": "openai", "Gemini": "gemini", "Claude": "claude",
    "DeepSeek API": "deepseek", "OpenRouter": "openrouter",
}

API_ENV_KEYS = {
    "Google AI Studio (Gemini free tier)": "GEMINI_API_KEY",
    "OpenAI GPT": "OPENAI_API_KEY", "Gemini": "GEMINI_API_KEY",
    "Claude": "ANTHROPIC_API_KEY", "DeepSeek API": "DEEPSEEK_API_KEY",
    "OpenRouter": "OPENROUTER_API_KEY",
}

MODEL_PRESETS = {
    "Ollama (local)": ["qwen2.5:7b-instruct", "qwen3:8b", "llama3.1:8b", "mistral:7b"],
    "Google AI Studio (Gemini free tier)": [
        "gemini-3.6-flash", "gemini-3.5-flash", "gemini-3.5-flash-lite",
        "gemini-3.1-pro-preview",
    ],
    "Gemini": ["gemini-3.6-flash", "gemini-3.5-flash", "gemini-3.1-pro-preview"],
    "OpenAI GPT": [
        "gpt-5.6", "gpt-5.6-sol", "gpt-5.6-terra", "gpt-5.6-luna",
        "gpt-5.5", "gpt-5.4", "gpt-5.4-mini", "gpt-5.4-nano",
    ],
    "Claude": ["claude-sonnet-5", "claude-opus-5", "claude-fable-5", "claude-haiku-4-5"],
    "DeepSeek API": ["deepseek-v4-flash", "deepseek-v4-pro"],
    "OpenRouter": ["openrouter/free"],
}


def model_options(provider_label: str, installed_ollama: list[str] | None = None) -> list[str]:
    options = list(MODEL_PRESETS[provider_label])
    if provider_label == "Ollama (local)":
        options = list(installed_ollama or []) + options
    return list(dict.fromkeys(options))
