#!/usr/bin/env python3
"""
Hermes Agent Gateway — Phase 2
FastAPI application providing unified API access to all 5 Hermes agents
with model routing, TPS budget management, and WebSocket streaming.
"""
import asyncio
import json
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .hermes_adapter import HermesAdapter
from .model_router import ModelRouter
from .tps_budget import TPSBudgetManager


# ─── Startup / Shutdown ──────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Hermes Agent Gateway starting...")
    app.state.router = ModelRouter()
    app.state.tps = TPSBudgetManager(limit=100)
    app.state.hermes = HermesAdapter(
        vps_host=os.environ["VPS_HOST"],
        vps_user=os.environ["VPS_USER"],
        ssh_key_path=os.environ.get("VPS_SSH_KEY", "/root/.ssh/id_ed25519"),
    )
    yield
    print("Hermes Agent Gateway shutting down...")


app = FastAPI(
    title="Hermes Agent Gateway",
    version="1.0.0",
    description="Unified gateway for all 5 Hermes agents",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Request / Response Models ────────────────────────────────────────────────

class ChatRequest(BaseModel):
    agent_id: str          # hermes1 … hermes5
    message: str
    stream: bool = False
    model_override: Optional[str] = None


class ChatResponse(BaseModel):
    agent_id: str
    message: str
    response: str
    model_used: dict
    tps_remaining: int


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "service": "hermes-agent-gateway"}


@app.get("/agents")
async def list_agents():
    return {
        "agents": [
            {"id": "hermes1", "role": "Planning Strategist",    "voice": "en-GB-MaisieNeural"},
            {"id": "hermes2", "role": "Creative Brainstormer",  "voice": "en-AU-CarlyNeural"},
            {"id": "hermes3", "role": "System Architect",       "voice": "en-KE-AsiliaNeural"},
            {"id": "hermes4", "role": "Bug Triage Specialist",  "voice": "en-US-TonyNeural"},
            {"id": "hermes5", "role": "Root Cause Analyst",     "voice": "en-US-ChristopherNeural"},
        ]
    }


@app.get("/models")
async def list_models():
    router: ModelRouter = app.state.router
    return {"models": router.available_models()}


@app.get("/tps")
async def tps_status():
    tps: TPSBudgetManager = app.state.tps
    return {"limit": tps.limit, "remaining": tps.remaining(), "window_seconds": 60}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    _validate_agent(req.agent_id)

    tps: TPSBudgetManager = app.state.tps
    if tps.remaining() <= 0:
        raise HTTPException(status_code=429, detail="TPS budget exhausted — try again in 60 seconds")

    router: ModelRouter = app.state.router
    model = router.select_model(req.agent_id, req.model_override)

    hermes: HermesAdapter = app.state.hermes
    response = await hermes.chat(req.agent_id, req.message, model)

    tps.consume(1)
    return ChatResponse(
        agent_id=req.agent_id,
        message=req.message,
        response=response,
        model_used=model,
        tps_remaining=tps.remaining(),
    )


@app.post("/api/chat/stream")
async def chat_stream(req: ChatRequest):
    _validate_agent(req.agent_id)

    tps: TPSBudgetManager = app.state.tps
    if tps.remaining() <= 0:
        raise HTTPException(status_code=429, detail="TPS budget exhausted")

    router: ModelRouter = app.state.router
    model = router.select_model(req.agent_id, req.model_override)
    hermes: HermesAdapter = app.state.hermes

    async def event_stream() -> AsyncGenerator[str, None]:
        async for chunk in hermes.stream(req.agent_id, req.message, model):
            yield f"data: {json.dumps({'chunk': chunk})}\n\n"
        yield "data: [DONE]\n\n"
        tps.consume(1)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    await websocket.accept()
    hermes: HermesAdapter = app.state.hermes
    router: ModelRouter = app.state.router
    tps: TPSBudgetManager = app.state.tps

    try:
        while True:
            data = await websocket.receive_json()
            agent_id = data.get("agent_id", "hermes1")
            message = data.get("message", "")

            if not message.strip():
                continue

            if tps.remaining() <= 0:
                await websocket.send_json({"error": "TPS budget exhausted"})
                continue

            model = router.select_model(agent_id, data.get("model_override"))
            async for chunk in hermes.stream(agent_id, message, model):
                await websocket.send_json({"chunk": chunk, "agent_id": agent_id})

            await websocket.send_json({"done": True, "tps_remaining": tps.remaining()})
            tps.consume(1)

    except WebSocketDisconnect:
        pass


# ─── Helpers ──────────────────────────────────────────────────────────────────

VALID_AGENTS = {"hermes1", "hermes2", "hermes3", "hermes4", "hermes5"}

def _validate_agent(agent_id: str):
    if agent_id not in VALID_AGENTS:
        raise HTTPException(status_code=400, detail=f"Invalid agent_id '{agent_id}'. Must be one of: {sorted(VALID_AGENTS)}")
