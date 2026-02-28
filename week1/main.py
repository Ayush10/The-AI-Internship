import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

BASE_PATH = os.environ.get("BASE_PATH", "")

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
from config import DEFAULT_PROVIDER, ANTHROPIC_API_KEY, OPENAI_API_KEY, GOOGLE_API_KEY, MESSAGE_LIMIT
from models import init_db, get_db, Conversation, Message, User
from history import router as history_router
from auth import router as auth_router

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
| **History** | All conversations are persisted and can be resumed |

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
    {
        "name": "History",
        "description": "Conversation history — list, view, rename, and delete past conversations.",
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
    root_path=BASE_PATH,
)

app.include_router(history_router)
app.include_router(auth_router)

STATIC_DIR = Path(__file__).parent / "static"


@app.on_event("startup")
def on_startup():
    init_db()


# --- Helpers for history persistence ---

def _save_messages(db: Session, conversation_id: UUID | None, user_content: str, assistant_content: str, meta: dict | None = None):
    if not conversation_id or not db:
        return
    convo = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not convo:
        return
    db.add(Message(conversation_id=convo.id, role="user", content=user_content))
    db.add(Message(conversation_id=convo.id, role="assistant", content=assistant_content, meta=meta))
    convo.updated_at = datetime.now(timezone.utc)
    db.commit()


def require_user_with_quota(
    fingerprint: str = Query(description="Browser fingerprint UUID"),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.fingerprint == fingerprint).first()
    if not user:
        raise HTTPException(403, "Not registered. Please complete the access gate.")
    if not user.is_admin and user.message_count >= MESSAGE_LIMIT:
        raise HTTPException(429, f"Message limit reached ({MESSAGE_LIMIT} messages). Contact admin for unlimited access.")
    return user, db


def _increment_message_count(user, db: Session):
    if not user.is_admin:
        user.message_count += 1
        db.commit()


@app.get(
    "/providers/status",
    tags=["Health"],
    summary="Provider Availability",
    description="Returns which LLM providers have API keys configured.",
)
def providers_status():
    return {
        "gemini": bool(GOOGLE_API_KEY),
        "openai": bool(OPENAI_API_KEY),
        "anthropic": bool(ANTHROPIC_API_KEY),
    }


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
- `conversation_id` — Append this interaction to an existing conversation

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
    conversation_id: UUID | None = Query(default=None, description="Conversation ID to append to"),
    user_quota: tuple = Depends(require_user_with_quota),
):
    user, db = user_quota
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

    summary_text = summary.strip()
    _save_messages(db, conversation_id, request.text, summary_text)
    _increment_message_count(user, db)

    return SummarizeResponse(
        summary=summary_text,
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
- `conversation_id` — Append this interaction to an existing conversation

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
    conversation_id: UUID | None = Query(default=None, description="Conversation ID to append to"),
    user_quota: tuple = Depends(require_user_with_quota),
):
    user, db = user_quota
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

    display = f"Sentiment: {parsed['sentiment']}\nConfidence: {parsed['confidence']}\nExplanation: {parsed['explanation']}"
    _save_messages(db, conversation_id, request.text, display, meta=parsed)
    _increment_message_count(user, db)

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
def chat(
    request: ChatRequest,
    conversation_id: UUID | None = Query(default=None, description="Conversation ID to append to"),
    user_quota: tuple = Depends(require_user_with_quota),
):
    user, db = user_quota
    system_prompt = CHAT_SYSTEM_PROMPTS.get(request.mode, CHAT_SYSTEM_PROMPTS["general"])
    llm = get_provider(request.provider)

    try:
        response = llm.generate_with_system(system_prompt, request.message, max_tokens=1024)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(502, f"LLM provider error: {e}")

    response_text = response.strip()
    _save_messages(db, conversation_id, request.message, response_text)
    _increment_message_count(user, db)

    return ChatResponse(response=response_text, provider=request.provider)


@app.post(
    "/enhance-prompt",
    response_model=EnhanceResponse,
    tags=["Chat & Tools"],
    summary="Enhance a Prompt",
    description="""Improve a raw prompt using established prompt engineering techniques from [promptingguide.ai](https://www.promptingguide.ai/).

Applies relevant techniques such as role prompting, specificity, chain-of-thought, few-shot cues, and output formatting.
""",
)
def enhance_prompt(
    request: EnhanceRequest,
    conversation_id: UUID | None = Query(default=None, description="Conversation ID to append to"),
    user_quota: tuple = Depends(require_user_with_quota),
):
    user, db = user_quota
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
        enhanced = data["enhanced_prompt"]
        techniques = data.get("techniques_applied", [])
    except (json.JSONDecodeError, KeyError):
        enhanced = raw.strip()
        techniques = ["raw_enhancement"]

    _save_messages(db, conversation_id, request.prompt, enhanced, meta={"techniques_applied": techniques})
    _increment_message_count(user, db)

    return EnhanceResponse(
        enhanced_prompt=enhanced,
        techniques_applied=techniques,
    )


# --- Static files (chat UI) ---

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", include_in_schema=False)
def serve_ui():
    html = (STATIC_DIR / "index.html").read_text()
    inject = f'<script>window.__BASE_PATH__ = "{BASE_PATH}";</script>'
    html = html.replace("</head>", f"{inject}</head>")
    return HTMLResponse(html)


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
