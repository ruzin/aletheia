"""Aletheia API proxy.

A thin FastAPI layer between the browser and the local vLLM OpenAI-compatible server.
Responsibilities:

- Expose exactly two logical models — ``base`` and ``tuned`` — and map them to the
  vLLM model names, so the browser never chooses arbitrary models or talks to vLLM
  directly.
- Stream tokens back to the browser as Server-Sent Events.
- Apply a light per-IP rate limit.

vLLM is started (see serving/vllm.service) with:
    vllm serve Qwen/Qwen2.5-7B-Instruct \
        --enable-lora --lora-modules aletheia=/opt/aletheia/adapter ...
so the two model names below resolve to the stock weights and the base+adapter.
"""
from __future__ import annotations

import json
import os
import time
from collections import defaultdict, deque

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

VLLM_URL = os.environ.get("VLLM_URL", "http://127.0.0.1:8000")
BASE_MODEL = os.environ.get("BASE_MODEL", "Qwen/Qwen2.5-7B-Instruct")
TUNED_MODEL = os.environ.get("TUNED_MODEL", "aletheia")

# Map the two logical panes to concrete vLLM model names.
MODELS = {"base": BASE_MODEL, "tuned": TUNED_MODEL}

# Optional per-pane system prompts. Kept empty by default so the divergence comes purely
# from the weights, not from prompt engineering — that is the honest version of the demo.
SYSTEM_PROMPTS = {
    "base": os.environ.get("BASE_SYSTEM_PROMPT", "").strip(),
    "tuned": os.environ.get("TUNED_SYSTEM_PROMPT", "").strip(),
}

MAX_TOKENS = int(os.environ.get("MAX_TOKENS", "512"))
RATE_LIMIT = int(os.environ.get("RATE_LIMIT_PER_MIN", "30"))

app = FastAPI(title="Aletheia proxy")
_hits: dict[str, deque] = defaultdict(deque)


class Turn(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    model: str = Field(..., description="'base' or 'tuned'")
    messages: list[Turn]
    temperature: float = 0.7
    max_tokens: int | None = None


def _rate_limited(ip: str) -> bool:
    now = time.time()
    q = _hits[ip]
    while q and now - q[0] > 60:
        q.popleft()
    if len(q) >= RATE_LIMIT:
        return True
    q.append(now)
    return False


def _build_messages(pane: str, messages: list[Turn]) -> list[dict]:
    out: list[dict] = []
    sys_prompt = SYSTEM_PROMPTS.get(pane, "")
    if sys_prompt:
        out.append({"role": "system", "content": sys_prompt})
    out.extend({"role": t.role, "content": t.content} for t in messages)
    return out


@app.get("/api/health")
async def health():
    async with httpx.AsyncClient(timeout=5) as client:
        try:
            r = await client.get(f"{VLLM_URL}/v1/models")
            up = r.status_code == 200
        except httpx.HTTPError:
            up = False
    return {"ok": up, "models": list(MODELS)}


@app.post("/api/chat")
async def chat(req: ChatRequest, request: Request):
    if req.model not in MODELS:
        raise HTTPException(400, f"model must be one of {list(MODELS)}")
    ip = request.client.host if request.client else "unknown"
    if _rate_limited(ip):
        raise HTTPException(429, "rate limit exceeded, please slow down")

    payload = {
        "model": MODELS[req.model],
        "messages": _build_messages(req.model, req.messages),
        "temperature": req.temperature,
        "max_tokens": req.max_tokens or MAX_TOKENS,
        "stream": True,
    }

    async def event_stream():
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream(
                "POST", f"{VLLM_URL}/v1/chat/completions", json=payload
            ) as resp:
                if resp.status_code != 200:
                    body = await resp.aread()
                    yield _sse({"error": body.decode("utf-8", "replace")})
                    return
                async for line in resp.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    data = line[len("data: "):]
                    if data == "[DONE]":
                        yield _sse({"done": True})
                        return
                    try:
                        chunk = json.loads(data)
                        delta = chunk["choices"][0]["delta"].get("content", "")
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue
                    if delta:
                        yield _sse({"token": delta})

    return StreamingResponse(event_stream(), media_type="text/event-stream")


def _sse(obj: dict) -> str:
    return f"data: {json.dumps(obj)}\n\n"
