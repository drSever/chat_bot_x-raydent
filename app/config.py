from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _flag(name: str, default: bool) -> bool:
    value = os.getenv(name)
    return default if value is None else value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    faq_path: Path = Path(os.getenv("XRAYDENT_FAQ_PATH", ROOT / "data" / "chatbot-faq-119.md"))
    embedding_model: str = os.getenv(
        "XRAYDENT_EMBEDDING_MODEL",
        "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    )
    llm_model: str = os.getenv("XRAYDENT_LLM_MODEL", "Qwen/Qwen3-0.6B")
    adapter_path: Path = Path(os.getenv("XRAYDENT_ADAPTER_PATH", ROOT / "artifacts" / "adapter"))
    enable_semantic: bool = _flag("XRAYDENT_ENABLE_SEMANTIC", True)
    enable_llm: bool = _flag("XRAYDENT_ENABLE_LLM", True)
    allow_general_knowledge: bool = _flag("XRAYDENT_ALLOW_GENERAL_KNOWLEDGE", False)
    offline: bool = _flag("XRAYDENT_OFFLINE", True)
    retrieval_threshold: float = float(os.getenv("XRAYDENT_RETRIEVAL_THRESHOLD", "0.55"))
    max_history: int = int(os.getenv("XRAYDENT_MAX_HISTORY", "6"))


settings = Settings()
