from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = Path(os.getenv("MTRD_DATA_DIR", PROJECT_ROOT / "data"))
CONFIG_DIR = Path(os.getenv("MTRD_CONFIG_DIR", PROJECT_ROOT / "config"))
CHROMA_DIR = Path(os.getenv("MTRD_CHROMA_DIR", PROJECT_ROOT / "data" / "chroma"))
SNAPSHOT_DIR = Path(os.getenv("MTRD_SNAPSHOT_DIR", PROJECT_ROOT / "data" / "snapshots"))
BRIEF_DIR = Path(os.getenv("MTRD_BRIEF_DIR", PROJECT_ROOT / "data" / "briefs"))
LOG_DIR = Path(os.getenv("MTRD_LOG_DIR", PROJECT_ROOT / "data" / "logs"))


@dataclass
class LLMConfig:
    backend: str = os.getenv("LLM_BACKEND", "ollama")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "phi3:latest")
    openai_base_url: str = os.getenv("OPENAI_BASE_URL", "http://localhost:11434/v1")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "ollama")
    timeout: int = int(os.getenv("MTRD_LLM_TIMEOUT", "60"))
    max_tokens: int = int(os.getenv("MTRD_LLM_MAX_TOKENS", "200"))
    temperature: float = float(os.getenv("MTRD_LLM_TEMPERATURE", "0.2"))
    no_tools: bool = os.getenv("MTRD_LLM_NO_TOOLS", "1") == "1"


@dataclass
class EmbeddingConfig:
    backend: str = os.getenv("EMBEDDINGS_BACKEND", "huggingface")
    hf_model: str = os.getenv("HF_EMBED_MODEL", "BAAI/bge-small-en-v1.5")


@dataclass
class AppConfig:
    llm: LLMConfig = LLMConfig()
    embeddings: EmbeddingConfig = EmbeddingConfig()
    top_k: int = int(os.getenv("MTRD_TOP_K", "6"))
    context_max_chars: int = int(os.getenv("MTRD_CONTEXT_MAX_CHARS", "6000"))
    extractive_only: bool = os.getenv("MTRD_EXTRACTIVE_ONLY", "1") == "1"


def ensure_dirs() -> None:
    for path in [DATA_DIR, CONFIG_DIR, CHROMA_DIR, SNAPSHOT_DIR, BRIEF_DIR, LOG_DIR]:
        path.mkdir(parents=True, exist_ok=True)
