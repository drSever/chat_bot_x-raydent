from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import ROOT, settings
from .safety import SENSITIVE_PATTERNS, _matches
from .schemas import ChatRequest, ChatResponse, FeedbackRequest, SupportRequest
from .service import ChatService

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
service = ChatService(settings)
STATIC = ROOT / "app" / "static"


@asynccontextmanager
async def lifespan(_: FastAPI):
    service.initialize()
    yield


app = FastAPI(title="X-RayDent Support Bot", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/", include_in_schema=False)
def demo_page() -> FileResponse:
    return FileResponse(STATIC / "index.html")


@app.get("/api/health")
def health() -> dict:
    return service.health()


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    return service.chat(request)


@app.post("/api/feedback")
def feedback(request: FeedbackRequest) -> dict:
    service.feedback[request.rating] += 1
    return {"accepted": True, "totals": dict(service.feedback)}


@app.post("/api/support/demo")
def support_demo(request: SupportRequest) -> dict:
    if _matches(SENSITIVE_PATTERNS, request.description.lower()):
        raise HTTPException(
            status_code=422,
            detail="Удалите пароли, коды, полные медицинские документы и персональные данные.",
        )
    return {
        "accepted": True,
        "demo": True,
        "message": "Демо-обращение проверено, но не было отправлено или сохранено.",
    }
