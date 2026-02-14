import json
import re
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.openapi.utils import get_openapi

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

DESCRIPTION = """
## AI-Powered Text Analysis API

A multi-provider LLM gateway built with FastAPI for the **AI Engineering Bootcamp**.
Supports **OpenAI GPT-4o Mini**, **Anthropic Claude Sonnet**, and **Google Gemini Flash**.

### Core Capabilities

| Feature | Description |
|---------|-------------|
| **Summarization** | Condense long texts with configurable prompt strategies |
| **Sentiment Analysis** | Classify text as positive, negative, or neutral with confidence scores |
| **Chat** | Interactive conversation with mode-specific system prompts |
| **Prompt Enhancement** | Improve raw prompts using prompt engineering best practices |

### Prompt Engineering

Each analysis endpoint supports **3 prompt variations** to compare engineering techniques:
- **v1** — Direct and minimal
- **v2** — Role assignment with guided rules *(default)*
- **v3** — Chain-of-thought reasoning

Switch between strategies using the `prompt_version` query parameter.
"""

tags_metadata = [
    {
        "name": "Health",
        "description": "Service health monitoring.",
    },
    {
        "name": "Text Analysis",
        "description": "Core NLP endpoints — summarization and sentiment analysis powered by LLMs.",
    },
    {
        "name": "Chat & Tools",
        "description": "Interactive chat and prompt engineering utilities.",
    },
]

app = FastAPI(
    title="The AI Internship API",
    summary="Multi-provider LLM gateway for text summarization, sentiment analysis, and chat.",
    description=DESCRIPTION,
    version="1.0.0",
    openapi_tags=tags_metadata,
    license_info={
        "name": "MIT",
    },
    docs_url="/docs",
    redoc_url="/redoc",
)

STATIC_DIR = Path(__file__).parent / "static"


# --- API Endpoints (assignment requirement) ---

@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["Health"],
    summary="Health Check",
    description="Returns the current service status and UTC timestamp. Use this to verify the API is running.",
)
def health():
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@app.post(
    "/summarize",
    response_model=SummarizeResponse,
    tags=["Text Analysis"],
    summary="Summarize Text",
    description="""Generate a concise summary of the provided text using an LLM.

**Query Parameters:**
- `provider` — Override the default LLM provider (`gemini`, `openai`, `anthropic`)
- `prompt_version` — Select a prompt engineering strategy (1, 2, or 3)

**Prompt Strategies:**
| Version | Technique | Description |
|---------|-----------|-------------|
| 1 | Direct | Minimal instruction — "Summarize in N words" |
| 2 | Guided *(default)* | Expert role + explicit rules + output anchor |
| 3 | Chain-of-Thought | Identify key points first, then summarize |
""",
)
def summarize(
    request: SummarizeRequest,
    provider: str = Query(default=None, description="LLM provider to use (gemini, openai, anthropic)"),
    prompt_version: int = Query(default=None, description="Prompt template version (1, 2, or 3)"),
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


@app.post(
    "/analyze-sentiment",
    response_model=SentimentResponse,
    tags=["Text Analysis"],
    summary="Analyze Sentiment",
    description="""Classify the sentiment of the provided text as **positive**, **negative**, or **neutral**.

Returns a confidence score (0.0 to 1.0) and a brief explanation.

**Query Parameters:**
- `provider` — Override the default LLM provider (`gemini`, `openai`, `anthropic`)
- `prompt_version` — Select a prompt engineering strategy (1, 2, or 3)

**Prompt Strategies:**
| Version | Technique | Description |
|---------|-----------|-------------|
| 1 | Direct JSON | Explicit JSON format request, no examples |
| 2 | Few-Shot *(default)* | Expert role + example output |
| 3 | Step-by-Step | Chain-of-thought reasoning before JSON |
""",
)
def analyze_sentiment(
    request: SentimentRequest,
    provider: str = Query(default=None, description="LLM provider to use (gemini, openai, anthropic)"),
    prompt_version: int = Query(default=None, description="Prompt template version (1, 2, or 3)"),
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

@app.post(
    "/chat",
    response_model=ChatResponse,
    tags=["Chat & Tools"],
    summary="Chat with AI",
    description="""Send a message to an AI assistant with mode-specific behavior.

**Modes:**
- `general` — General-purpose helpful assistant
- `summarize` — Summarization-focused assistant
- `sentiment` — Sentiment analysis-focused assistant
""",
)
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


@app.post(
    "/enhance-prompt",
    response_model=EnhanceResponse,
    tags=["Chat & Tools"],
    summary="Enhance a Prompt",
    description="""Improve a raw prompt using established prompt engineering techniques from [promptingguide.ai](https://www.promptingguide.ai/).

Applies relevant techniques such as role prompting, specificity, chain-of-thought, few-shot cues, and output formatting.
""",
)
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


@app.get("/", include_in_schema=False)
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
