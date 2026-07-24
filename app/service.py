from __future__ import annotations

import threading
import uuid
from collections import Counter

from .config import Settings
from .faq import parse_faq
from .generator import LocalGenerator
from .retrieval import FaqRetriever, normalize
from .safety import route_safety
from .schemas import ChatRequest, ChatResponse, FaqSource


class ChatService:
    def __init__(self, config: Settings):
        self.config = config
        self.entries = parse_faq(config.faq_path)
        self.retriever = FaqRetriever(self.entries, config.embedding_model, config.enable_semantic)
        self.generator = LocalGenerator(config.llm_model, config.adapter_path, config.enable_llm, config.offline)
        self.feedback = Counter()
        self._model_lock = threading.Lock()

    def initialize(self) -> None:
        self.retriever.load(local_files_only=self.config.offline)
        self.generator.load()

    def chat(self, request: ChatRequest) -> ChatResponse:
        response_id = uuid.uuid4().hex
        decision = route_safety(request.message)
        if decision:
            return ChatResponse(
                response_id=response_id,
                answer=decision.answer,
                source_type="safety",
                confidence=1.0,
                safety_flag=decision.flag,
                escalation=decision.escalation,
                model_mode=self.generator.mode,
            )
        hits = self.retriever.search(request.message, top_k=3)
        confidence = hits[0].score if hits else 0.0
        grounded = bool(hits and confidence >= self.config.retrieval_threshold)
        contexts = [hit.entry for hit in hits] if grounded else []
        history = [item.model_dump() for item in request.history[-self.config.max_history:]]
        if not grounded and not self.config.allow_general_knowledge:
            answer = (
                "Я не нашёл подтверждённого ответа в справке X‑RayDent и не буду придумывать. "
                "Уточните, вопрос относится к сервису, отчёту, доступу, оплате или клинической ситуации, "
                "либо откройте демо-форму поддержки."
            )
            source_type = "fallback"
        elif normalize(request.message) == normalize(hits[0].entry.question):
            # Exact FAQ questions should remain stable and verbatim. The LLM
            # is reserved for paraphrases that benefit from natural phrasing.
            answer = hits[0].entry.answer
            source_type = "faq"
        else:
            with self._model_lock:
                answer = self.generator.answer(request.message, contexts, history)
            source_type = "faq" if grounded else ("general" if self.generator.ready else "fallback")
        sources = [
            FaqSource(id=hit.entry.id, section=hit.entry.section, question=hit.entry.question, score=hit.score)
            for hit in hits
        ] if grounded else []
        return ChatResponse(
            response_id=response_id,
            answer=answer,
            source_type=source_type,
            sources=sources,
            confidence=confidence,
            escalation=None if grounded else "support",
            model_mode=self.generator.mode,
        )

    def health(self) -> dict:
        return {
            "status": "ok",
            "faq_entries": len(self.entries),
            "retrieval": "semantic" if self.retriever.semantic_ready else "lexical-fallback",
            "retrieval_error": self.retriever.semantic_error,
            "llm": "ready" if self.generator.ready else "fallback",
            "llm_error": self.generator.load_error,
            "adapter": self.generator.adapter_loaded,
            "model_mode": self.generator.mode,
        }
