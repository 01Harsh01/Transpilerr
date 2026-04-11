from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import httpx
import os
from pydantic import BaseModel
from typing import Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="code.friend API", version="2.0.0")

# ── CORS — allow your frontend domain ──
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-sonnet-4-20250514"

# ── Request Models ──
class TranspileRequest(BaseModel):
    source_code: str
    from_lang: str
    to_lang: str
    extra_instructions: Optional[str] = ""

class ExplainRequest(BaseModel):
    source_code: str
    language: str

class ReviewRequest(BaseModel):
    source_code: str
    language: str

class SimulateRequest(BaseModel):
    code: str
    language: str

class ChatRequest(BaseModel):
    message: str
    code: Optional[str] = ""
    language: Optional[str] = ""


# ── Helper ──
async def call_claude(system: str, user: str, max_tokens: int = 4096) -> dict:
    if not ANTHROPIC_API_KEY:
        raise HTTPException(status_code=500, detail="API key not configured on server.")

    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": MODEL,
        "max_tokens": max_tokens,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(ANTHROPIC_URL, headers=headers, json=payload)

    if resp.status_code != 200:
        err = resp.json()
        raise HTTPException(status_code=resp.status_code,
                            detail=err.get("error", {}).get("message", "Claude API error"))

    data = resp.json()
    text = "".join(b["text"] for b in data["content"] if b["type"] == "text")
    usage = data.get("usage", {})
    return {"result": text, "usage": usage}


# ── Routes ──
@app.get("/")
async def root():
    return {"status": "ok", "service": "code.friend API", "version": "2.0.0"}

@app.get("/health")
async def health():
    key_configured = bool(ANTHROPIC_API_KEY)
    return {"status": "ok", "api_key_configured": key_configured}


@app.post("/transpile")
async def transpile(req: TranspileRequest):
    if not req.source_code.strip():
        raise HTTPException(status_code=400, detail="source_code is required")
    if req.from_lang == req.to_lang:
        raise HTTPException(status_code=400, detail="from_lang and to_lang must be different")

    system = f"""You are an expert code transpiler and software engineer.
Convert code from {req.from_lang} to {req.to_lang}.

Rules:
1. Return ONLY the transpiled code — no explanations, no markdown fences, no preamble
2. The code must be clean, idiomatic {req.to_lang}
3. Preserve all logic, structure, and comments from the source
4. Use {req.to_lang} best practices and naming conventions
5. If the source uses libraries/frameworks, use the closest {req.to_lang} equivalents
{f"Additional instructions: {req.extra_instructions}" if req.extra_instructions else ""}"""

    user = f"Convert this {req.from_lang} code to {req.to_lang}:\n\n{req.source_code}"
    logger.info(f"Transpile: {req.from_lang} → {req.to_lang} ({len(req.source_code)} chars)")
    return await call_claude(system, user)


@app.post("/explain")
async def explain(req: ExplainRequest):
    if not req.source_code.strip():
        raise HTTPException(status_code=400, detail="source_code is required")

    system = f"""You are a friendly, expert coding assistant.
Explain the given {req.language} code clearly.
Cover: what it does, how it works step by step, key concepts/patterns used, and any gotchas or potential issues.
Format your explanation in clear sections. Be concise but thorough."""

    user = f"Explain this {req.language} code:\n\n{req.source_code}"
    logger.info(f"Explain: {req.language} ({len(req.source_code)} chars)")
    return await call_claude(system, user, max_tokens=2048)


@app.post("/review")
async def review(req: ReviewRequest):
    if not req.source_code.strip():
        raise HTTPException(status_code=400, detail="source_code is required")

    system = f"""You are a senior software engineer doing a code review.
Review the given {req.language} code and provide actionable feedback.
Check for: bugs, security vulnerabilities, performance issues, code style, readability, and best practices.
Be specific — reference line numbers or code snippets where possible.
End with a short summary and overall rating (1-10)."""

    user = f"Review this {req.language} code:\n\n{req.source_code}"
    logger.info(f"Review: {req.language} ({len(req.source_code)} chars)")
    return await call_claude(system, user, max_tokens=2048)


@app.post("/simulate")
async def simulate(req: SimulateRequest):
    if not req.code.strip():
        raise HTTPException(status_code=400, detail="code is required")

    system = f"""You are a precise code execution simulator.
Mentally execute the given {req.language} code and return ONLY what it would print to stdout/console.
No explanation. No markdown. Just the raw terminal output.
If nothing is printed, return exactly: (no output)
Keep output under 20 lines."""

    user = f"Simulate execution of this {req.language} code:\n\n{req.code}"
    logger.info(f"Simulate: {req.language}")
    return await call_claude(system, user, max_tokens=512)


@app.post("/chat")
async def chat(req: ChatRequest):
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="message is required")

    code_context = f"\n\nCurrent code context ({req.language}):\n```\n{req.code}\n```" if req.code else ""

    system = f"""You are code.friend — a helpful, friendly AI coding assistant.
You help developers with coding questions, debugging, explanations, and best practices.
Be concise, practical, and friendly.{code_context}"""

    user = req.message
    logger.info(f"Chat: {req.message[:60]}...")
    return await call_claude(system, user, max_tokens=1024)
