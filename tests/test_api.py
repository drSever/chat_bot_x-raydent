from dataclasses import replace

from fastapi.testclient import TestClient

from app import main
from app.config import settings
from app.schemas import ChatRequest
from app.service import ChatService


def test_api_without_downloaded_models(monkeypatch):
    config = replace(settings, enable_semantic=False, enable_llm=False)
    test_service = ChatService(config)
    test_service.generator.answer = lambda *_: (_ for _ in ()).throw(AssertionError("LLM must not handle exact FAQ"))
    monkeypatch.setattr(main, "service", test_service)
    with TestClient(main.app) as client:
        health = client.get("/api/health")
        assert health.status_code == 200
        assert health.json()["faq_entries"] == 119
        response = client.post("/api/chat", json={"message": "Что такое X-RayDent?", "session_id": "test", "history": []})
        assert response.status_code == 200
        payload = response.json()
        assert payload["source_type"] == "faq"
        assert payload["sources"][0]["id"] == 1
        assert "цифровая платформа" in payload["answer"]


def test_support_demo_does_not_accept_password(monkeypatch):
    config = replace(settings, enable_semantic=False, enable_llm=False)
    monkeypatch.setattr(main, "service", ChatService(config))
    with TestClient(main.app) as client:
        response = client.post("/api/support/demo", json={"category": "technical", "description": "Мой пароль: qwerty, сайт не работает"})
        assert response.status_code == 422


def test_unknown_question_without_general_model_points_to_email(monkeypatch):
    config = replace(settings, enable_semantic=False, enable_llm=False, allow_general_knowledge=False)
    test_service = ChatService(config)
    monkeypatch.setattr(main, "service", test_service)
    with TestClient(main.app) as client:
        response = client.post(
            "/api/chat",
            json={"message": "Кто написал Войну и мир?", "session_id": "general", "history": []},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["source_type"] == "fallback"
        assert "не буду придумывать" in payload["answer"]
        assert "info@x-raydent.ru" in payload["answer"]


def test_unknown_question_uses_cautious_model_answer_and_email():
    config = replace(settings, enable_semantic=False, enable_llm=True, allow_general_knowledge=True)
    test_service = ChatService(config)
    test_service.generator.model = object()
    test_service.generator.tokenizer = object()
    test_service.generator.answer = lambda *_: "Возможно, такая возможность предусмотрена."
    test_service.retriever.search = lambda *_args, **_kwargs: []

    response = test_service.chat(
        ChatRequest(message="Есть ли экспорт в нестандартный формат?", session_id="general")
    )

    assert response.source_type == "general"
    assert "может быть приблизительным" in response.answer
    assert "Возможно" in response.answer
    assert "info@x-raydent.ru" in response.answer
