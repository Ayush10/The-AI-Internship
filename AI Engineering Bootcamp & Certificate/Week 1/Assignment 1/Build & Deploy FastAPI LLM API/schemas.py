from pydantic import BaseModel
from typing import Literal


class HealthResponse(BaseModel):
    status: str
    timestamp: str


class SummarizeRequest(BaseModel):
    text: str
    max_length: int = 100


class SummarizeResponse(BaseModel):
    summary: str
    provider: str
    prompt_version: int


class SentimentRequest(BaseModel):
    text: str


class SentimentResponse(BaseModel):
    sentiment: Literal["positive", "negative", "neutral"]
    confidence: float
    explanation: str
    provider: str
    prompt_version: int


class ChatRequest(BaseModel):
    message: str
    provider: str = "openai"
    mode: Literal["general", "summarize", "sentiment"] = "general"


class ChatResponse(BaseModel):
    response: str
    provider: str


class EnhanceRequest(BaseModel):
    prompt: str


class EnhanceResponse(BaseModel):
    enhanced_prompt: str
    techniques_applied: list[str]
