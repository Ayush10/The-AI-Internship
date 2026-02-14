import json
import re
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from schemas import (
    HealthResponse,
    SummarizeRequest, SummarizeResponse,
    SentimentRequest, SentimentResponse,
    ChatRequest, ChatResponse,
    EnhanceRequest, EnhanceResponse,
)
from providers import get_provider
from prompts import (
    SUMMARIZE_PROMPTS, DEFAULT_SUMMARIZE_PROMPT,
    SENTIMENT_PROMPTS, DEFAULT_SENTIMENT_PROMPT,
    CHAT_SYSTEM_PROMPTS, ENHANCE_PROMPT_SYSTEM,
)
from config import DEFAULT_PROVIDER

app = FastAPI(title="LLM Summarizer & Sentiment API")

STATIC_DIR = Path(__file__).parent / "static"


# --- API Endpoints (assignment requirement) ---

@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@app.post("/summarize", response_model=SummarizeResponse)
def summarize(
    request: SummarizeRequest,
    provider: str = Query(default=None),
    prompt_version: int = Query(default=None),
):
    provider_name = provider or DEFAULT_PROVIDER
    version = prompt_version or DEFAULT_SUMMARIZE_PROMPT

    prompt_template = SUMMARIZE_PROMPTS.get(version)
    if not prompt_template:
        raise HTTPException(400, f"Invalid prompt_version: {version}. Choose 1, 2, or 3.")

    prompt = prompt_template.format(text=request.text, max_length=request.max_length)
    llm = get_provider(provider_name)

    try:
        summary = llm.generate(prompt, max_tokens=request.max_length * 2)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(502, f"LLM provider error: {e}")

    return SummarizeResponse(
        summary=summary.strip(),
        provider=provider_name,
        prompt_version=version,
    )


@app.post("/analyze-sentiment", response_model=SentimentResponse)
def analyze_sentiment(
    request: SentimentRequest,
    provider: str = Query(default=None),
    prompt_version: int = Query(default=None),
):
    provider_name = provider or DEFAULT_PROVIDER
    version = prompt_version or DEFAULT_SENTIMENT_PROMPT

    prompt_template = SENTIMENT_PROMPTS.get(version)
    if not prompt_template:
        raise HTTPException(400, f"Invalid prompt_version: {version}. Choose 1, 2, or 3.")

    prompt = prompt_template.format(text=request.text)
    llm = get_provider(provider_name)

    try:
        raw_response = llm.generate(prompt, max_tokens=256)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(502, f"LLM provider error: {e}")

    parsed = _parse_sentiment_json(raw_response)

    return SentimentResponse(
        sentiment=parsed["sentiment"],
        confidence=parsed["confidence"],
        explanation=parsed["explanation"],
        provider=provider_name,
        prompt_version=version,
    )


# --- Chat & Enhancement Endpoints (UI support) ---

@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    system_prompt = CHAT_SYSTEM_PROMPTS.get(request.mode, CHAT_SYSTEM_PROMPTS["general"])
    llm = get_provider(request.provider)

    try:
        response = llm.generate_with_system(system_prompt, request.message, max_tokens=1024)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(502, f"LLM provider error: {e}")

    return ChatResponse(response=response.strip(), provider=request.provider)


@app.post("/enhance-prompt", response_model=EnhanceResponse)
def enhance_prompt(request: EnhanceRequest):
    provider_name = DEFAULT_PROVIDER
    llm = get_provider(provider_name)

    try:
        raw = llm.generate_with_system(
            ENHANCE_PROMPT_SYSTEM,
            f"Enhance this prompt:\n\n{request.prompt}",
            max_tokens=1024,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(502, f"LLM provider error: {e}")

    try:
        cleaned = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("`")
        data = json.loads(cleaned)
        return EnhanceResponse(
            enhanced_prompt=data["enhanced_prompt"],
            techniques_applied=data.get("techniques_applied", []),
        )
    except (json.JSONDecodeError, KeyError):
        return EnhanceResponse(
            enhanced_prompt=raw.strip(),
            techniques_applied=["raw_enhancement"],
        )


# --- Static files (chat UI) ---

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
def serve_ui():
    return FileResponse(str(STATIC_DIR / "index.html"))


# --- Helpers ---

def _parse_sentiment_json(raw: str) -> dict:
    cleaned = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("`")

    json_match = re.search(r'\{[^{}]*"sentiment"[^{}]*\}', cleaned, re.DOTALL)
    if json_match:
        cleaned = json_match.group()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        raise HTTPException(502, f"LLM returned invalid JSON: {raw[:200]}")

    sentiment = data.get("sentiment", "").lower().strip()
    if sentiment not in ("positive", "negative", "neutral"):
        raise HTTPException(502, f"LLM returned invalid sentiment: {sentiment}")

    return {
        "sentiment": sentiment,
        "confidence": float(data.get("confidence", 0.5)),
        "explanation": data.get("explanation", "No explanation provided"),
    }
