from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import httpx
import os
from pydantic import BaseModel
from typing import Optional
import logging
 
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
 
app = FastAPI(title="code.friend API", version="4.0.0")
 
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
 
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.3-70b-versatile"
 
# ── Models ──
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
 
# ── Groq helper ──
async def call_groq(system: str, user: str, max_tokens: int = 4096) -> str:
    if not GROQ_API_KEY:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY not configured on server.")
 
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": MODEL,
        "max_tokens": max_tokens,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
    }
 
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(GROQ_URL, headers=headers, json=payload)
 
    if resp.status_code != 200:
        err = resp.json()
        msg = err.get("error", {}).get("message", "Groq API error")
        raise HTTPException(status_code=resp.status_code, detail=msg)
 
    data = resp.json()
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError):
        raise HTTPException(status_code=500, detail="Unexpected Groq response format")
 
# ── Routes ──
@app.get("/")
async def root():
    return {"status": "ok", "service": "code.friend", "version": "4.0.0", "model": MODEL}
 
@app.get("/health")
async def health():
    return {"status": "ok", "api_key_configured": bool(GROQ_API_KEY)}
 
@app.post("/transpile")
async def transpile(req: TranspileRequest):
    if not req.source_code.strip():
        raise HTTPException(status_code=400, detail="source_code is required")
    if req.from_lang == req.to_lang:
        raise HTTPException(status_code=400, detail="from_lang and to_lang must be different")
 
    system = f"""You are an expert code transpiler and software engineer.
Convert code from {req.from_lang} to {req.to_lang}.
 
STRICT RULES:
- Return ONLY the raw transpiled code
- NO markdown code fences (no ```)
- NO explanations, NO preamble
- Preserve comments from the original
- The code must be clean and idiomatic {req.to_lang}
- Use {req.to_lang} best practices and naming conventions
{f"- Additional instructions: {req.extra_instructions}" if req.extra_instructions else ""}"""
 
    user = f"Convert this {req.from_lang} code to {req.to_lang}:\n\n{req.source_code}"
    logger.info(f"Transpile: {req.from_lang} → {req.to_lang} ({len(req.source_code)} chars)")
    result = await call_groq(system, user, max_tokens=4096)
    result = result.strip()
    if result.startswith("```"):
        lines = result.split("\n")
        result = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])
    return {"result": result.strip()}
 
@app.post("/explain")
async def explain(req: ExplainRequest):
    if not req.source_code.strip():
        raise HTTPException(status_code=400, detail="source_code is required")
 
    system = f"""You are a friendly expert coding assistant.
Explain {req.language} code clearly and concisely.
Cover: what it does, how it works step by step, key concepts, and potential issues.
Use plain text only, no markdown."""
 
    user = f"Explain this {req.language} code:\n\n{req.source_code}"
    logger.info(f"Explain: {req.language}")
    result = await call_groq(system, user, max_tokens=2048)
    return {"result": result.strip()}
 
@app.post("/review")
async def review(req: ReviewRequest):
    if not req.source_code.strip():
        raise HTTPException(status_code=400, detail="source_code is required")
 
    system = f"""You are a senior software engineer doing a thorough code review.
Review {req.language} code and give actionable feedback on:
- Bugs or logical errors
- Security vulnerabilities
- Performance issues
- Code style and readability
- Best practice violations
- Suggested improvements
Be specific, reference line numbers where possible.
End with an overall rating out of 10.
Use plain text only, no markdown."""
 
    user = f"Review this {req.language} code:\n\n{req.source_code}"
    logger.info(f"Review: {req.language}")
    result = await call_groq(system, user, max_tokens=2048)
    return {"result": result.strip()}
 
@app.post("/simulate")
async def simulate(req: SimulateRequest):
    if not req.code.strip():
        raise HTTPException(status_code=400, detail="code is required")
 
    system = f"""You are a precise code execution simulator.
Mentally execute the {req.language} code and return ONLY what prints to stdout/console.
No explanation. No markdown. Just raw terminal output.
If nothing prints, return exactly: (no output)
Maximum 20 lines."""
 
    user = f"Simulate this {req.language} code:\n\n{req.code}"
    logger.info(f"Simulate: {req.language}")
    result = await call_groq(system, user, max_tokens=512)
    return {"result": result.strip()}
 
@app.post("/chat")
async def chat(req: ChatRequest):
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="message is required")
 
    code_ctx = f"\n\nCurrent code in editor ({req.language}):\n{req.code[:2000]}" if req.code else ""
 
    system = f"""You are code.friend — a helpful, friendly AI coding assistant.
Help with coding questions, debugging, explanations, and best practices.
Be concise, practical and friendly. Plain text only.{code_ctx}"""
 
    user = req.message
    logger.info(f"Chat: {req.message[:50]}")
    result = await call_groq(system, user, max_tokens=1024)
    return {"result": result.strip()}
 
