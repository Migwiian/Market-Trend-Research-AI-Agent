from __future__ import annotations

from llama_index.core import Settings

from mtrd.config import AppConfig


def get_embed_model(config: AppConfig):
    backend = config.embeddings.backend
    if backend == "mock":
        from llama_index.core.embeddings.mock import MockEmbedding

        return MockEmbedding(embed_dim=384)
    if backend == "huggingface":
        try:
            from llama_index.embeddings.huggingface import HuggingFaceEmbedding
        except Exception as exc:
            raise RuntimeError("Install llama-index-embeddings-huggingface") from exc
        return HuggingFaceEmbedding(model_name=config.embeddings.hf_model)
    raise ValueError(f"Unknown embeddings backend: {backend}")


def get_llm(config: AppConfig):
    backend = config.llm.backend
    if backend == "ollama":
        try:
            from llama_index.llms.ollama import Ollama
        except Exception as exc:
            raise RuntimeError("Install llama-index-llms-ollama") from exc
        return Ollama(model=config.llm.ollama_model)
    raise ValueError(f"Unknown LLM backend: {backend}")


def configure_llm(config: AppConfig) -> None:
    Settings.llm = get_llm(config)
