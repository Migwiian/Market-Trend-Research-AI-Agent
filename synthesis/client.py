from __future__ import annotations

import os
from dataclasses import dataclass

from pydantic_ai.models.openai import OpenAIChatModel


@dataclass
class LLMConfig:
    base_url: str = os.getenv("LLM_BASE_URL", "http://localhost:11434/v1")
    api_key: str = os.getenv("LLM_API_KEY", "ollama")
    fast_model: str = os.getenv("LLM_FAST_MODEL", "phi3:latest")
    standard_model: str = os.getenv("LLM_STANDARD_MODEL", "llama3.1:8b")
    timeout: int = int(os.getenv("LLM_TIMEOUT", "120"))
    fast_max_tokens: int = int(os.getenv("LLM_FAST_MAX_TOKENS", "700"))
    standard_max_tokens: int = int(os.getenv("LLM_STANDARD_MAX_TOKENS", "1200"))
    temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.2"))
    use_mock: bool = os.getenv("LLM_USE_MOCK", "0") == "1"


def model_name_for_tier(tier: str, config: LLMConfig) -> str:
    if tier == "fast":
        return config.fast_model
    if tier == "standard":
        return config.standard_model
    raise ValueError(f"Unknown tier: {tier}")


def build_model(tier: str, config: LLMConfig) -> OpenAIChatModel:
    model_name = model_name_for_tier(tier, config)
    os.environ.setdefault("OPENAI_BASE_URL", config.base_url)
    os.environ.setdefault("OPENAI_API_KEY", config.api_key)
    max_tokens = config.fast_max_tokens if tier == "fast" else config.standard_max_tokens
    return OpenAIChatModel(
        model_name=model_name,
        provider="openai-chat",
        settings={
            "timeout": config.timeout,
            "max_tokens": max_tokens,
            "temperature": config.temperature,
        },
    )
