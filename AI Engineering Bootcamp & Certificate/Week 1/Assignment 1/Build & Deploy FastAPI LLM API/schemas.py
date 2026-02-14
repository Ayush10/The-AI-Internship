from pydantic import BaseModel, Field
from typing import Literal


class HealthResponse(BaseModel):
    status: str = Field(description="Current service status", examples=["healthy"])
    timestamp: str = Field(description="UTC timestamp in ISO 8601 format", examples=["2026-02-14T14:46:03.083645+00:00"])

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"status": "healthy", "timestamp": "2026-02-14T14:46:03.083645+00:00"}
            ]
        }
    }


class SummarizeRequest(BaseModel):
    text: str = Field(
        description="The text to summarize",
        examples=["Artificial intelligence has transformed industries from healthcare to finance. Machine learning models can now diagnose diseases, predict market trends, and automate complex workflows that previously required human expertise."],
    )
    max_length: int = Field(
        default=100,
        description="Maximum number of words in the summary",
        examples=[100],
        ge=10,
        le=1000,
    )


class SummarizeResponse(BaseModel):
    summary: str = Field(description="The generated summary of the input text")
    provider: str = Field(description="LLM provider used for generation", examples=["gemini"])
    prompt_version: int = Field(description="Prompt template version used (1, 2, or 3)", examples=[2])


class SentimentRequest(BaseModel):
    text: str = Field(
        description="The text to analyze for sentiment",
        examples=["I absolutely loved this product! The quality exceeded my expectations and the customer service was outstanding."],
    )


class SentimentResponse(BaseModel):
    sentiment: Literal["positive", "negative", "neutral"] = Field(
        description="Detected sentiment classification",
        examples=["positive"],
    )
    confidence: float = Field(
        description="Confidence score from 0.0 (uncertain) to 1.0 (certain)",
        examples=[0.92],
        ge=0.0,
        le=1.0,
    )
    explanation: str = Field(
        description="Brief explanation of the sentiment analysis",
        examples=["The text expresses strong enthusiasm and satisfaction with both the product quality and service."],
    )
    provider: str = Field(description="LLM provider used for analysis", examples=["gemini"])
    prompt_version: int = Field(description="Prompt template version used (1, 2, or 3)", examples=[2])


class ChatRequest(BaseModel):
    message: str = Field(
        description="The message to send to the AI assistant",
        examples=["Explain the difference between supervised and unsupervised learning."],
    )
    provider: str = Field(
        default="gemini",
        description="LLM provider to use",
        examples=["gemini"],
    )
    mode: Literal["general", "summarize", "sentiment"] = Field(
        default="general",
        description="Chat mode — determines the assistant's behavior",
        examples=["general"],
    )


class ChatResponse(BaseModel):
    response: str = Field(description="The AI assistant's response")
    provider: str = Field(description="LLM provider used", examples=["gemini"])


class EnhanceRequest(BaseModel):
    prompt: str = Field(
        description="The raw prompt to enhance using prompt engineering techniques",
        examples=["Write a poem about AI"],
    )


class EnhanceResponse(BaseModel):
    enhanced_prompt: str = Field(description="The improved prompt with applied techniques")
    techniques_applied: list[str] = Field(
        description="List of prompt engineering techniques that were applied",
        examples=[["role_prompting", "specificity", "output_format"]],
    )
