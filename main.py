from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import httpx
import os
from pydantic import BaseModel
from typing import Optional
import logging
 
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
 
app = FastAPI(title="code.friend API", version="3.0.0")
 
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
 
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
 
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
 
# ── Gemini helper ──
async def call_gemini(prompt: str, max_tokens: int = 4096) -> str:
    if not GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY not configured on server.")
 
    url = f"{GEMINI_URL}?key={GEMINI_API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "maxOutputTokens": max_tokens,
            "temperature": 0.2,
        }
    }
 
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(url, json=payload)
 
    if resp.status_code != 200:
        err = resp.json()
        msg = err.get("error", {}).get("message", "Gemini API error")
        raise HTTPException(status_code=resp.status_code, detail=msg)
 
    data = resp.json()
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        raise HTTPException(status_code=500, detail="Unexpected Gemini response format")
 
# ── Routes ──
@app.get("/")
async def root():
    return {"status": "ok", "service": "code.friend", "version": "3.0.0", "model": "gemini-2.0-flash"}
 
@app.get("/health")
async def health():
    return {"status": "ok", "api_key_configured": bool(GEMINI_API_KEY)}
 
@app.post("/transpile")
async def transpile(req: TranspileRequest):
    if not req.source_code.strip():
        raise HTTPException(status_code=400, detail="source_code is required")
    if req.from_lang == req.to_lang:
        raise HTTPException(status_code=400, detail="from_lang and to_lang must be different")
 
    prompt = f"""You are an expert code transpiler. Convert the following {req.from_lang} code to {req.to_lang}.
 
STRICT RULES:
- Return ONLY the raw transpiled code
- NO markdown code fences (no ```)
- NO explanations, NO preamble, NO comments unless they existed in the original
- The code must be clean, idiomatic {req.to_lang}
- Preserve all logic and structure
- Use {req.to_lang} best practices
{f"- Additional: {req.extra_instructions}" if req.extra_instructions else ""}
 
{req.from_lang} code to convert:
 
{req.source_code}"""
 
    logger.info(f"Transpile: {req.from_lang} → {req.to_lang} ({len(req.source_code)} chars)")
    result = await call_gemini(prompt, max_tokens=4096)
    # Strip any accidental markdown fences
    result = result.strip()
    if result.startswith("```"):
        lines = result.split("\n")
        result = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])
    return {"result": result.strip()}
 
@app.post("/explain")
async def explain(req: ExplainRequest):
    if not req.source_code.strip():
        raise HTTPException(status_code=400, detail="source_code is required")
 
    prompt = f"""You are a friendly expert coding assistant. Explain the following {req.language} code clearly.
 
Cover:
1. What the code does (overview)
2. How it works step by step
3. Key concepts and patterns used
4. Any potential issues or improvements
 
Be concise but thorough. Use plain text, no markdown.
 
{req.language} code:
 
{req.source_code}"""
 
    logger.info(f"Explain: {req.language}")
    result = await call_gemini(prompt, max_tokens=2048)
    return {"result": result.strip()}
 
@app.post("/review")
async def review(req: ReviewRequest):
    if not req.source_code.strip():
        raise HTTPException(status_code=400, detail="source_code is required")
 
    prompt = f"""You are a senior software engineer doing a thorough code review.
 
Review the following {req.language} code and provide actionable feedback on:
- Bugs or logical errors
- Security vulnerabilities
- Performance issues
- Code style and readability
- Best practices violations
- Suggested improvements
 
Be specific. Reference line numbers or snippets where possible.
End with an overall rating out of 10 and a one-line summary.
Use plain text, no markdown.
 
{req.language} code:
 
{req.source_code}"""
 
    logger.info(f"Review: {req.language}")
    result = await call_gemini(prompt, max_tokens=2048)
    return {"result": result.strip()}
 
@app.post("/simulate")
async def simulate(req: SimulateRequest):
    if not req.code.strip():
        raise HTTPException(status_code=400, detail="code is required")
 
    prompt = f"""You are a precise code execution simulator.
 
Mentally execute the following {req.language} code and return ONLY what would be printed to stdout/console.
- No explanation
- No markdown
- Just the raw terminal output exactly as it would appear
- If nothing is printed, return exactly: (no output)
- Maximum 20 lines
 
{req.language} code:
 
{req.code}"""
 
    logger.info(f"Simulate: {req.language}")
    result = await call_gemini(prompt, max_tokens=512)
    return {"result": result.strip()}
 
@app.post("/chat")
async def chat(req: ChatRequest):
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="message is required")
 
    code_ctx = f"\n\nCurrent code in editor ({req.language}):\n{req.code[:2000]}" if req.code else ""
 
    prompt = f"""You are code.friend — a helpful, friendly AI coding assistant.
Help developers with coding questions, debugging, explanations, and best practices.
Be concise, practical and friendly. Use plain text.{code_ctx}
 
User asks: {req.message}"""
 
    logger.info(f"Chat: {req.message[:50]}")
    result = await call_gemini(prompt, max_tokens=1024)
    return {"result": result.strip()}
