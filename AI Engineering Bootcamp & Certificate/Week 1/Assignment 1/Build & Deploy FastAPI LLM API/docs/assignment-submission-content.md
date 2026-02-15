# Week 1 Assignment: Build & Deploy FastAPI LLM API

## Deployment & Source Code

- **Live API URL**: https://theaiinternship.ayushojha.com
- **API Documentation**: https://theaiinternship.ayushojha.com/docs
- **GitHub Repository**: https://github.com/Ayush10/The-AI-Internship

---

## API Endpoints Overview

The API provides 3 core LLM-powered endpoints, each supporting multiple providers (Gemini, OpenAI, Anthropic) and 3 prompt engineering variations:

| # | Endpoint | Method | Purpose |
|---|----------|--------|---------|
| 1 | `/summarize` | POST | Text summarization with configurable length |
| 2 | `/analyze-sentiment` | POST | Sentiment classification with confidence scores |
| 3 | `/chat` | POST | Interactive AI chat with mode-specific behavior |

Additional endpoints: `/health` (health check), `/enhance-prompt` (prompt improvement tool), and full conversation history CRUD.

---

## Screenshots: All 3 Endpoints Working

### 1. Health Check — `GET /health`

```json
{
    "status": "healthy",
    "timestamp": "2026-02-15T00:54:09.772000+00:00"
}
```

### 2. Summarize Endpoint — `POST /summarize`

**Request:**
```json
POST /summarize?provider=gemini&prompt_version=2
{
    "text": "Artificial intelligence has transformed the way businesses operate across every industry. From healthcare diagnostics that can detect diseases earlier than human doctors, to financial algorithms that process millions of transactions per second, AI is reshaping our world at an unprecedented pace. However, this rapid advancement also raises important ethical questions about job displacement, algorithmic bias, and the concentration of power among a few technology companies. As we move forward, finding the right balance between innovation and responsible development will be crucial for ensuring AI benefits all of humanity, not just a privileged few.",
    "max_length": 50
}
```

**Response:**
```json
{
    "summary": "AI is rapidly transforming industries, from healthcare to finance, but raises ethical concerns. Job displacement, bias, and power concentration are key challenges. Balancing innovation with responsible development is crucial to ensure AI benefits everyone.",
    "provider": "gemini",
    "prompt_version": 2
}
```

### 3. Sentiment Analysis Endpoint — `POST /analyze-sentiment`

**Request:**
```json
POST /analyze-sentiment?provider=gemini&prompt_version=2
{
    "text": "I absolutely loved the new restaurant downtown. The food was incredible and the service was amazing. Best dining experience I have had in years."
}
```

**Response:**
```json
{
    "sentiment": "positive",
    "confidence": 0.99,
    "explanation": "The text uses strong positive words like \"loved\", \"incredible\", and \"amazing\" to describe a fantastic restaurant experience.",
    "provider": "gemini",
    "prompt_version": 2
}
```

### 4. Chat Endpoint — `POST /chat`

**Request:**
```json
POST /chat
{
    "message": "What are the top 3 benefits of using FastAPI for building APIs?",
    "provider": "gemini",
    "mode": "general"
}
```

**Response:**
```json
{
    "response": "1. **High Performance:** FastAPI is built on top of Starlette and Pydantic, enabling it to offer performance comparable to NodeJS and Go.\n2. **Fast Development:** Features like automatic data validation and auto-generation of API documentation (using OpenAPI and JSON Schema) significantly speed up development.\n3. **Easy to Use:** Its intuitive design and comprehensive documentation make it easy for developers of all levels to learn and use.",
    "provider": "gemini"
}
```

---

## Prompt Engineering Experiments

### Summarize Endpoint — 3 Prompt Variations

**Test Input:** A paragraph about AI transforming industries, ethical concerns, and the need for responsible development (100+ words).

#### Variation 1: Direct and Minimal
**Strategy:** Simple, direct instruction with no framing or role assignment.
```
Summarize the following text in {max_length} words or fewer. Return only the summary, nothing else.
```

**Output (Gemini):**
```
AI is revolutionizing industries with advancements in healthcare and finance, but raises ethical concerns like job displacement and bias. Balancing innovation with responsible development is essential to ensure AI benefits everyone.
```

**Quality Notes:** Concise and clean. Follows the word limit. However, it misses the nuance about "concentration of power" — the summary is slightly surface-level.

---

#### Variation 2: Guided with Rules (Default — Best)
**Strategy:** Role assignment ("expert summarizer") + explicit rules + output anchor word "Summary:".
```
You are an expert summarizer. Read the following text carefully and produce a concise summary.
Rules:
- Maximum {max_length} words
- Capture the main idea and key supporting points
- Use clear, simple language
- Do not add information not present in the original text
```

**Output (Gemini):**
```
AI is rapidly transforming industries, from healthcare to finance, but raises ethical concerns. Job displacement, bias, and power concentration are key challenges. Balancing innovation with responsible development is crucial to ensure AI benefits everyone.
```

**Quality Notes:** Captures all three key themes (transformation, ethical concerns, balance needed). Mentions "power concentration" which V1 missed. The role assignment and explicit rules produced a more thorough yet still concise result.

---

#### Variation 3: Chain-of-Thought
**Strategy:** Two-step reasoning — first identify key points, then summarize.
```
Read the following text. First, identify the 2-3 most important points. Then, write a summary of no more than {max_length} words that covers those points.
```

**Output (Gemini):**
```
**Important Points:**
1. AI is rapidly transforming businesses across industries.
2. AI advancements raise ethical concerns (job displacement, bias, power concentration).
3. Balancing innovation with responsible development is crucial for equitable benefits.

**Summary:**
AI is rapidly changing businesses and industries but raises ethical concerns regarding job displacement, bias, and power concentration. Balancing innovation with responsible development is crucial to ensure AI benefits everyone equitably.
```

**Quality Notes:** Most thorough analysis — explicitly lists key points before summarizing. However, it leaks the intermediate reasoning into the output (the "Important Points" section), making it less suitable when you only want a clean summary. The actual summary is excellent though.

---

#### Best Variation: **Variation 2 (Guided with Rules)**

**Why:** V2 produced the best balance of completeness and format compliance. The role prompt ("expert summarizer") focused the model, and the explicit rules (word limit, key points, simple language, no hallucination) acted as guardrails. Unlike V1, it captured all nuances. Unlike V3, it returned a clean summary without leaking intermediate reasoning. This aligns with the prompting guide's recommendation that **structured constraints + role prompting** yield the most reliable outputs for production APIs.

---

### Sentiment Analysis Endpoint — 3 Prompt Variations

**Test Input 1 (Clear positive):** "I absolutely loved the new restaurant downtown. The food was incredible and the service was amazing. Best dining experience I have had in years."

**Test Input 2 (Ambiguous/neutral):** "The product arrived on time and works as expected. Nothing special but it gets the job done. The packaging could have been better though."

#### Variation 1: Direct JSON Instruction
**Strategy:** Explicit JSON format request with no examples or role.
```
Analyze the sentiment of the following text. Respond with ONLY a JSON object in this exact format, no other text:
{"sentiment": "positive" or "negative" or "neutral", "confidence": 0.0 to 1.0, "explanation": "brief explanation"}
```

**Output (Positive text):**
```json
{"sentiment": "positive", "confidence": 0.98, "explanation": "The text expresses strong positive emotions through words like 'absolutely loved,' 'incredible,' and 'amazing,' indicating a very favorable experience."}
```

**Output (Ambiguous text):**
```json
{"sentiment": "neutral", "confidence": 0.7, "explanation": "The text contains both positive (arrived on time, works as expected, gets the job done) and negative (packaging could have been better, nothing special) elements, resulting in an overall neutral sentiment."}
```

**Quality Notes:** Correct classifications. Format compliance is good. The explanation for the ambiguous text correctly identifies the mixed signals. Confidence of 0.7 for the ambiguous text is reasonable.

---

#### Variation 2: Role + Few-Shot Example (Default — Best)
**Strategy:** Expert role assignment + one example output (few-shot prompting).
```
You are a sentiment analysis expert. Analyze the sentiment of the given text.
Classify as exactly one of: positive, negative, neutral.
Rate confidence from 0.0 to 1.0. Provide a one-sentence explanation.
Example output: {"sentiment": "positive", "confidence": 0.85, "explanation": "The text expresses enthusiasm and satisfaction."}
```

**Output (Positive text):**
```json
{"sentiment": "positive", "confidence": 0.99, "explanation": "The text uses strong positive words like \"loved\", \"incredible\", and \"amazing\" to describe a fantastic restaurant experience."}
```

**Output (Ambiguous text):**
```json
{"sentiment": "neutral", "confidence": 0.75, "explanation": "The text expresses satisfaction with the product's basic functionality but also includes a minor criticism, resulting in an overall neutral sentiment."}
```

**Quality Notes:** Highest format compliance across runs — the few-shot example anchors the model to the exact output structure. Higher confidence calibration (0.99 vs 0.98 for clear positive, 0.75 vs 0.7 for ambiguous). The role framing produces more professional explanations.

---

#### Variation 3: Step-by-Step Analysis (Chain-of-Thought)
**Strategy:** Guided reasoning (tone, mixed signals, confidence assessment) before JSON output.
```
Analyze the sentiment step by step:
1. What is the overall tone?
2. Are there mixed signals or conflicting sentiments?
3. How confident are you?
Then provide JSON with: sentiment, confidence, explanation.
```

**Output (Positive text):**
```json
{"sentiment": "positive", "confidence": 1.0, "explanation": "The text expresses strong positive emotions through words like 'absolutely loved,' 'incredible,' and 'amazing,' indicating a highly positive sentiment."}
```

**Output (Ambiguous text):**
```json
{"sentiment": "neutral", "confidence": 0.8, "explanation": "The text contains both positive (on-time delivery, functionality) and negative (packaging) aspects, resulting in an overall neutral sentiment."}
```

**Quality Notes:** The chain-of-thought reasoning produced the highest confidence scores (1.0 for clear positive, 0.8 for ambiguous). The step-by-step process makes the model more decisive. However, confidence of 1.0 for any sentiment task is arguably overconfident — V2's 0.99 is more realistic. The explanation quality is comparable to V2.

---

#### Best Variation: **Variation 2 (Role + Few-Shot Example)**

**Why:** V2 consistently produced the best combination of format reliability, confidence calibration, and explanation quality. The few-shot example is the key differentiator — by showing the model exactly what the output should look like, it achieves near-perfect JSON format compliance every time. The role prompt adds analytical depth. V1 works but lacks the structural anchor. V3 produces good analysis but tends toward overconfidence (1.0 scores). For a production API where consistent JSON parsing is critical, V2's few-shot approach is the most reliable.

---

## Prompt Engineering Summary

Studying the Prompt Engineering Guide at promptingguide.ai provided a strong foundation for understanding how the structure and specificity of prompts directly impact LLM output quality. The most impactful techniques I applied were **role prompting** (assigning the model an expert persona to focus its responses), **few-shot prompting** (providing example outputs to anchor the format), and **chain-of-thought prompting** (asking the model to reason step-by-step before answering). Each technique addresses a different failure mode: role prompting reduces generic responses, few-shot examples eliminate format inconsistency, and chain-of-thought improves accuracy on complex or ambiguous inputs.

Through hands-on experimentation with my API's three prompt variations, I discovered that the most effective prompts combine multiple techniques rather than relying on a single approach. My best-performing prompts (Variation 2 for both endpoints) used role prompting together with explicit constraints and few-shot examples. This combination gave the model clear "guardrails" — it knew what role to play, what rules to follow, and what the output should look like. In contrast, the minimal V1 prompts worked but produced shallower results, while the chain-of-thought V3 prompts sometimes leaked intermediate reasoning into the final output, which is problematic for APIs that need clean, parseable responses.

The most practical insight from the guide is that prompt engineering is fundamentally about **reducing ambiguity**. Every technique — whether it is specifying output format, providing examples, assigning roles, or adding constraints — serves to narrow the space of possible responses. For API development specifically, this means treating prompts like function signatures: the more precisely you define the expected input-output contract, the more reliable and consistent your API responses become. This directly informed my decision to make V2 (structured constraints + few-shot) the default for both endpoints, as it optimizes for the production requirement of consistent, well-formatted outputs.
