"""Local MLX backend for the Aletheia web app — no GPU / no AWS.

Serves the SAME /api contract as the production FastAPI proxy (serving/proxy/main.py),
but runs inference on Apple Silicon via MLX instead of vLLM. It loads two 4-bit models so
both fit comfortably in 32 GB:

  base  -> stock Qwen2.5-7B (4-bit)
  tuned -> stock Qwen2.5-7B (4-bit) + the LoRA adapter from finetune/adapters

Run it, then point the web dev server at it:

  source finetune/.venv/bin/activate
  pip install fastapi "uvicorn[standard]" pydantic
  python serving/local_mlx_server.py                 # http://127.0.0.1:8080

  cd web && VITE_API_TARGET=http://127.0.0.1:8080 npm run dev
"""
import json
import os
import threading
from typing import List, Optional

import uvicorn
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from mlx_lm import load, stream_generate

BASE_REPO = os.environ.get("BASE_REPO", "mlx-community/Qwen2.5-7B-Instruct-4bit")
ADAPTER = os.environ.get("ADAPTER_PATH", "finetune/adapters")
MAX_TOKENS = int(os.environ.get("MAX_TOKENS", "512"))
PORT = int(os.environ.get("PORT", "8080"))

app = FastAPI(title="Aletheia local MLX server")

print(f"loading base  : {BASE_REPO}")
_base = load(BASE_REPO)
print(f"loading tuned : {BASE_REPO} + adapter {ADAPTER}")
_tuned = load(BASE_REPO, adapter_path=ADAPTER)
MODELS = {"base": _base, "tuned": _tuned}

# MLX generation is not re-entrant; serialise the two panes' requests.
_lock = threading.Lock()


class Turn(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    model: str
    messages: List[Turn]
    temperature: float = 0.7
    max_tokens: Optional[int] = None


def _sse(obj: dict) -> str:
    return f"data: {json.dumps(obj)}\n\n"


@app.get("/api/health")
def health():
    return {"ok": True, "models": list(MODELS)}


@app.post("/api/chat")
def chat(req: ChatRequest):
    if req.model not in MODELS:
        return StreamingResponse(
            iter([_sse({"error": f"model must be one of {list(MODELS)}"})]),
            media_type="text/event-stream",
        )
    model, tok = MODELS[req.model]
    prompt = tok.apply_chat_template(
        [m.model_dump() for m in req.messages], add_generation_prompt=True, tokenize=False
    )

    def gen():
        with _lock:
            for resp in stream_generate(
                model, tok, prompt, max_tokens=req.max_tokens or MAX_TOKENS
            ):
                yield _sse({"token": resp.text})
        yield _sse({"done": True})

    return StreamingResponse(gen(), media_type="text/event-stream")


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=PORT)
