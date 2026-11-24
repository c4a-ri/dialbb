"""Initialize chat models with readable errors for missing API keys."""

import os
import sys
from typing import Any

from langchain.chat_models import init_chat_model as _init_chat_model


def init_chat_model(model: str, **kwargs: Any) -> Any:
    """Check API-key authentication before constructing a LangChain model."""
    provider = kwargs.get("model_provider")
    if not provider and ":" in model:
        provider = model.split(":", 1)[0]
    if not provider:
        name = model.lower()
        if name.startswith(("gpt-", "o1", "o3", "chatgpt", "text-davinci")):
            provider = "openai"
        elif name.startswith("claude"):
            provider = "anthropic"

    provider = (provider or "").replace("-", "_").lower()
    key_names = {
        "openai": ("OPENAI_API_KEY",),
        "anthropic": ("ANTHROPIC_API_KEY",),
        "google_genai": ("GOOGLE_API_KEY", "GEMINI_API_KEY"),
    }.get(provider, ())

    # Vertex AI can authenticate with Google Cloud credentials instead of a key.
    if provider == "google_genai":
        vertexai = kwargs.get("vertexai")
        if vertexai is None:
            setting = os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", "").lower()
            vertexai = setting in ("true", "1", "yes") or (
                setting not in ("false", "0", "no") and (
                    kwargs.get("credentials") is not None
                    or kwargs.get("project") is not None
                )
            )
        if vertexai:
            key_names = ()

    if key_names and not any(
        kwargs.get(key) for key in ("api_key", "openai_api_key", "anthropic_api_key", "google_api_key")
    ) and not any(os.environ.get(key, "").strip() for key in key_names):
        variables = " or ".join(key_names)
        print(
            f"LLM Error: API key for model '{model}' is not set. "
            f"Set the {variables} environment variable and try again.",
            file=sys.stderr,
        )
        sys.exit(1)

    return _init_chat_model(model, **kwargs)
