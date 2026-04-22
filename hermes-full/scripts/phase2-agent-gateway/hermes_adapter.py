#!/usr/bin/env python3
"""
Hermes Adapter — executes prompts inside running Hermes Docker containers
via SSH, then routes through the selected model provider (cloud or local GPU).
"""
import asyncio
import json
import os
from typing import AsyncGenerator, Dict, Optional

import asyncssh
import httpx


# Hermes container name → channel role
AGENT_CHANNELS = {
    "hermes1": "general",
    "hermes2": "planning",
    "hermes3": "design",
    "hermes4": "issues",
    "hermes5": "problems",
}


class HermesAdapter:
    def __init__(self, vps_host: str, vps_user: str, ssh_key_path: str):
        self.vps_host = vps_host
        self.vps_user = vps_user
        self.ssh_key_path = ssh_key_path
        self._minimax_key = os.environ.get("MINIMAX_API_KEY", "")
        self._siliconflow_key = os.environ.get("SILICONFLOW_API_KEY", "")

    async def chat(self, agent_id: str, message: str, model: Dict) -> str:
        """Send a message and return the full response string."""
        chunks = []
        async for chunk in self.stream(agent_id, message, model):
            chunks.append(chunk)
        return "".join(chunks)

    async def stream(self, agent_id: str, message: str, model: Dict) -> AsyncGenerator[str, None]:
        """Yield response chunks from the selected model."""
        provider = model.get("provider", "cloud")

        if provider == "local":
            async for chunk in self._stream_local(agent_id, message, model):
                yield chunk
        elif model.get("service") == "minimax":
            async for chunk in self._stream_minimax(agent_id, message, model):
                yield chunk
        else:
            async for chunk in self._stream_siliconflow(agent_id, message, model):
                yield chunk

    # ── Local GPU (Ollama/LM Studio) ──────────────────────────────────────────

    async def _stream_local(self, agent_id: str, message: str, model: Dict) -> AsyncGenerator[str, None]:
        system_prompt = await self._get_agent_system_prompt(agent_id)
        url = f"{model['url']}/api/chat"
        payload = {
            "model": model["model"],
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message},
            ],
            "stream": True,
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream("POST", url, json=payload) as resp:
                async for line in resp.aiter_lines():
                    if line.strip():
                        try:
                            data = json.loads(line)
                            content = data.get("message", {}).get("content", "")
                            if content:
                                yield content
                        except json.JSONDecodeError:
                            pass

    # ── MiniMax ───────────────────────────────────────────────────────────────

    async def _stream_minimax(self, agent_id: str, message: str, model: Dict) -> AsyncGenerator[str, None]:
        system_prompt = await self._get_agent_system_prompt(agent_id)
        url = f"{model['base_url']}/chat/completions"
        payload = {
            "model": model["model"],
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message},
            ],
            "stream": True,
        }
        headers = {"Authorization": f"Bearer {self._minimax_key}"}
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream("POST", url, json=payload, headers=headers) as resp:
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        raw = line[6:]
                        if raw.strip() == "[DONE]":
                            break
                        try:
                            data = json.loads(raw)
                            delta = data["choices"][0]["delta"].get("content", "")
                            if delta:
                                yield delta
                        except (json.JSONDecodeError, KeyError):
                            pass

    # ── SiliconFlow ───────────────────────────────────────────────────────────

    async def _stream_siliconflow(self, agent_id: str, message: str, model: Dict) -> AsyncGenerator[str, None]:
        system_prompt = await self._get_agent_system_prompt(agent_id)
        url = f"{model['base_url']}/chat/completions"
        payload = {
            "model": model["model"],
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message},
            ],
            "stream": True,
        }
        headers = {"Authorization": f"Bearer {self._siliconflow_key}"}
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream("POST", url, json=payload, headers=headers) as resp:
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        raw = line[6:]
                        if raw.strip() == "[DONE]":
                            break
                        try:
                            data = json.loads(raw)
                            delta = data["choices"][0]["delta"].get("content", "")
                            if delta:
                                yield delta
                        except (json.JSONDecodeError, KeyError):
                            pass

    # ── SSH helper: fetch agent SOUL.md as system prompt ─────────────────────

    async def _get_agent_system_prompt(self, agent_id: str) -> str:
        try:
            async with asyncssh.connect(
                self.vps_host,
                username=self.vps_user,
                client_keys=[self.ssh_key_path],
                known_hosts=None,
            ) as conn:
                result = await conn.run(
                    f"docker exec {agent_id} cat /root/.hermes/SOUL.md 2>/dev/null || echo ''",
                    check=False,
                )
                soul = result.stdout.strip()
                return soul if soul else f"You are {agent_id}, a Hermes AI assistant."
        except Exception:
            return f"You are {agent_id}, a Hermes AI assistant."
