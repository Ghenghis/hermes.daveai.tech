#!/usr/bin/env python3
"""
Model Router — selects the best available model for each request.
Priority: Local GPU (RTX 3090 Ti) → Local GPU (AMD 7800XT) → MiniMax → SiliconFlow
"""
import os
from typing import Dict, List, Optional

import httpx


# Agent → task complexity mapping used to pick model tier
AGENT_COMPLEXITY = {
    "hermes1": "high",    # Planning Strategist
    "hermes2": "medium",  # Creative Brainstormer
    "hermes3": "high",    # System Architect
    "hermes4": "medium",  # Bug Triage Specialist
    "hermes5": "high",    # Root Cause Analyst
}

# Cloud model definitions
MINIMAX_MODELS = {
    "high":   "minimax/minimax-m2.5",
    "medium": "minimax/minimax-m2.5-highspeed",
    "low":    "minimax/minimax-m2.5-highspeed",
}

SILICONFLOW_MODELS = {
    "high":   "Qwen/Qwen2.5-72B-Instruct",
    "medium": "Qwen/Qwen2.5-7B-Instruct",
    "low":    "Qwen/Qwen2.5-7B-Instruct",
}


class ModelRouter:
    def __init__(self):
        self.rtx_url = os.environ.get("RTX_3090_URL", "")   # Tailscale IP:port
        self.amd_url = os.environ.get("AMD_7800_URL", "")   # Tailscale IP:port
        self.minimax_key = os.environ.get("MINIMAX_API_KEY", "")
        self.siliconflow_key = os.environ.get("SILICONFLOW_API_KEY", "")

    def select_model(self, agent_id: str, override: Optional[str] = None) -> Dict:
        """Return the best available model config for this agent."""
        if override:
            return self._override_model(override)

        complexity = AGENT_COMPLEXITY.get(agent_id, "medium")

        # 1. Try RTX 3090 Ti (primary local GPU)
        if self.rtx_url and self._gpu_reachable(self.rtx_url):
            return {
                "provider": "local",
                "gpu": "rtx3090ti",
                "url": self.rtx_url,
                "model": "llama-3-70b-instruct" if complexity == "high" else "llama-3-8b-instruct",
                "cost": 0.0,
            }

        # 2. Try AMD 7800XT (secondary local GPU)
        if self.amd_url and self._gpu_reachable(self.amd_url):
            return {
                "provider": "local",
                "gpu": "amd7800xt",
                "url": self.amd_url,
                "model": "llama-3-8b-instruct",
                "cost": 0.0,
            }

        # 3. MiniMax cloud fallback
        if self.minimax_key:
            return {
                "provider": "cloud",
                "service": "minimax",
                "base_url": "https://api.minimaxi.chat/v1",
                "model": MINIMAX_MODELS[complexity],
                "cost": 0.01,
            }

        # 4. SiliconFlow fallback
        if self.siliconflow_key:
            return {
                "provider": "cloud",
                "service": "siliconflow",
                "base_url": "https://api.siliconflow.com/v1",
                "model": SILICONFLOW_MODELS[complexity],
                "cost": 0.005,
            }

        raise RuntimeError("No model available — configure at least one of: RTX_3090_URL, AMD_7800_URL, MINIMAX_API_KEY, SILICONFLOW_API_KEY")

    def available_models(self) -> List[Dict]:
        models = []
        if self.rtx_url and self._gpu_reachable(self.rtx_url):
            models.append({"provider": "local", "gpu": "rtx3090ti", "status": "online"})
        if self.amd_url and self._gpu_reachable(self.amd_url):
            models.append({"provider": "local", "gpu": "amd7800xt", "status": "online"})
        if self.minimax_key:
            models.append({"provider": "cloud", "service": "minimax", "status": "configured"})
        if self.siliconflow_key:
            models.append({"provider": "cloud", "service": "siliconflow", "status": "configured"})
        return models

    def _gpu_reachable(self, url: str) -> bool:
        try:
            with httpx.Client(timeout=2.0) as client:
                resp = client.get(f"{url}/api/tags")
                return resp.status_code == 200
        except Exception:
            return False

    def _override_model(self, model_str: str) -> Dict:
        """Parse a manual override like 'siliconflow:deepseek-ai/DeepSeek-V3'."""
        if ":" in model_str:
            service, model = model_str.split(":", 1)
        else:
            service, model = "siliconflow", model_str

        if service == "minimax":
            return {"provider": "cloud", "service": "minimax", "base_url": "https://api.minimaxi.chat/v1", "model": model, "cost": 0.01}
        return {"provider": "cloud", "service": "siliconflow", "base_url": "https://api.siliconflow.com/v1", "model": model, "cost": 0.005}
