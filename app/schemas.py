from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class HistoryItem(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=2000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    session_id: str = Field(default="anonymous", min_length=1, max_length=100)
    history: list[HistoryItem] = Field(default_factory=list, max_length=12)

    @field_validator("message")
    @classmethod
    def message_not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Сообщение не может быть пустым")
        return value


class FaqSource(BaseModel):
    id: int
    section: str
    question: str
    score: float


class ChatResponse(BaseModel):
    response_id: str
    answer: str
    source_type: Literal["faq", "general", "safety", "fallback"]
    sources: list[FaqSource] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    safety_flag: str | None = None
    escalation: Literal["doctor", "urgent_care", "support"] | None = None
    model_mode: str


class FeedbackRequest(BaseModel):
    response_id: str = Field(min_length=1, max_length=100)
    rating: Literal["up", "down"]


class SupportRequest(BaseModel):
    category: Literal["service", "report", "access", "payment", "technical", "other"]
    description: str = Field(min_length=10, max_length=1000)

    @field_validator("description")
    @classmethod
    def description_not_blank(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 10:
            raise ValueError("Опишите ситуацию хотя бы в 10 символах")
        return value
