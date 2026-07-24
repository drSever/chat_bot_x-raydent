from __future__ import annotations

import logging
import math
import os
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Sequence

from .faq import FaqEntry

logger = logging.getLogger(__name__)


def normalize(text: str) -> str:
    return " ".join(re.findall(r"[a-zа-яё0-9]+", text.lower().replace("ё", "е")))


RUSSIAN_SUFFIXES = (
    "иями", "ями", "ами", "ого", "ему", "ыми", "ими", "ией", "ий", "ый", "ой",
    "ые", "ие", "ую", "юю", "ов", "ев", "ам", "ям", "ах", "ях", "ом", "ем",
    "ы", "и", "а", "я", "у", "ю", "е",
)


def _tokens(text: str) -> set[str]:
    result = set()
    for word in normalize(text).split():
        stem = word
        if len(word) > 5:
            for suffix in RUSSIAN_SUFFIXES:
                if word.endswith(suffix) and len(word) - len(suffix) >= 4:
                    stem = word[:-len(suffix)]
                    break
        result.add(stem)
    return result


def lexical_score(query: str, candidate: str) -> float:
    q, c = normalize(query), normalize(candidate)
    if not q or not c:
        return 0.0
    if q == c:
        return 1.0
    q_tokens, c_tokens = _tokens(q), _tokens(c)
    jaccard = len(q_tokens & c_tokens) / max(1, len(q_tokens | c_tokens))
    sequence = SequenceMatcher(None, q, c).ratio()
    containment = len(q_tokens & c_tokens) / max(1, min(len(q_tokens), len(c_tokens)))
    return min(1.0, 0.45 * jaccard + 0.35 * sequence + 0.20 * containment)


@dataclass(frozen=True)
class SearchHit:
    entry: FaqEntry
    score: float


class FaqRetriever:
    def __init__(self, entries: Sequence[FaqEntry], model_name: str, enable_semantic: bool = True):
        self.entries = list(entries)
        self.model_name = model_name
        self.enable_semantic = enable_semantic
        self.model = None
        self.embeddings = None
        self.semantic_error: str | None = None

    @property
    def semantic_ready(self) -> bool:
        return self.model is not None and self.embeddings is not None

    def load(self, local_files_only: bool = False) -> None:
        if not self.enable_semantic or self.semantic_ready:
            return
        try:
            from sentence_transformers import SentenceTransformer

            model_source: str | Path = self.model_name
            cache_root = Path(os.getenv("HF_HOME", Path.home() / ".cache" / "huggingface")) / "hub"
            snapshots = cache_root / f"models--{self.model_name.replace('/', '--')}" / "snapshots"
            if snapshots.exists():
                local_snapshots = sorted(
                    (path for path in snapshots.iterdir() if path.is_dir()),
                    key=lambda path: path.stat().st_mtime,
                    reverse=True,
                )
                if local_snapshots:
                    model_source = local_snapshots[0]
            self.model = SentenceTransformer(str(model_source), local_files_only=local_files_only)
            texts = [f"{entry.question} {entry.answer}" for entry in self.entries]
            self.embeddings = self.model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
            self.semantic_error = None
        except Exception as exc:  # fallback is intentional for offline/test mode
            self.semantic_error = f"{type(exc).__name__}: {exc}"
            logger.warning("Semantic retrieval unavailable; lexical fallback enabled: %s", exc)
            self.model = None
            self.embeddings = None

    def search(self, query: str, top_k: int = 3) -> list[SearchHit]:
        lexical = [lexical_score(query, entry.question) for entry in self.entries]
        scores = lexical[:]
        if self.semantic_ready:
            query_embedding = self.model.encode([query], normalize_embeddings=True, show_progress_bar=False)[0]
            semantic = self.embeddings @ query_embedding
            scores = [max(0.0, min(1.0, 0.85 * float(s) + 0.15 * l)) for s, l in zip(semantic, lexical)]
        for idx, entry in enumerate(self.entries):
            if normalize(query) == normalize(entry.question):
                scores[idx] = 1.0
        ranked = sorted(enumerate(scores), key=lambda pair: pair[1], reverse=True)[:top_k]
        return [SearchHit(self.entries[idx], round(float(score), 4)) for idx, score in ranked if math.isfinite(score)]
