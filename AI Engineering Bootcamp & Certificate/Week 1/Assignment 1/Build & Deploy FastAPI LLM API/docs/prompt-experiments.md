# Prompt Engineering Experiments

## Methodology
- Tested 3 prompt variations per endpoint (summarize and sentiment analysis)
- Each variation tested across all 3 LLM providers (OpenAI GPT-4o Mini, Anthropic Claude Sonnet, Google Gemini Flash)
- Evaluated on: accuracy, format compliance, response quality, and consistency

---

## Summarize Endpoint

### Test Input
> *[Paste your test text here — use a 2-3 paragraph article or passage]*

### Variation 1: Direct and Minimal
**Strategy**: Simple, direct instruction with no framing.
```
Summarize the following text in {max_length} words or fewer. Return only the summary, nothing else.
```

**Results**:
| Provider | Output | Quality Notes |
|----------|--------|---------------|
| OpenAI   | *[paste output]* | |
| Anthropic | *[paste output]* | |
| Gemini   | *[paste output]* | |

### Variation 2: Guided with Rules
**Strategy**: Role assignment + explicit rules + output anchor.
```
You are an expert summarizer. Read the following text carefully and produce a concise summary.
Rules: Maximum {max_length} words, capture main idea and key points, use simple language, no hallucination.
```

**Results**:
| Provider | Output | Quality Notes |
|----------|--------|---------------|
| OpenAI   | *[paste output]* | |
| Anthropic | *[paste output]* | |
| Gemini   | *[paste output]* | |

### Variation 3: Chain-of-Thought
**Strategy**: Ask the model to identify key points first, then summarize.
```
Read the following text. First, identify the 2-3 most important points. Then, write a summary of no more than {max_length} words.
```

**Results**:
| Provider | Output | Quality Notes |
|----------|--------|---------------|
| OpenAI   | *[paste output]* | |
| Anthropic | *[paste output]* | |
| Gemini   | *[paste output]* | |

### Best Variation: **[TBD]**
**Why**: *[Explain which variation produced the best summaries and why]*

---

## Sentiment Analysis Endpoint

### Test Input
> *[Paste your test text here — try both clearly positive/negative text and something ambiguous]*

### Variation 1: Direct JSON Instruction
**Strategy**: Explicit JSON format request, no examples.
```
Analyze the sentiment. Respond with ONLY a JSON object: {"sentiment": ..., "confidence": ..., "explanation": ...}
```

**Results**:
| Provider | Output | Format OK? | Accurate? |
|----------|--------|------------|-----------|
| OpenAI   | *[paste]* | | |
| Anthropic | *[paste]* | | |
| Gemini   | *[paste]* | | |

### Variation 2: Role + Few-Shot Example
**Strategy**: Expert role + one example output (few-shot prompting).
```
You are a sentiment analysis expert. [instructions...] Example output: {"sentiment": "positive", "confidence": 0.85, ...}
```

**Results**:
| Provider | Output | Format OK? | Accurate? |
|----------|--------|------------|-----------|
| OpenAI   | *[paste]* | | |
| Anthropic | *[paste]* | | |
| Gemini   | *[paste]* | | |

### Variation 3: Step-by-Step Analysis
**Strategy**: Chain-of-thought reasoning before JSON output.
```
Think through: 1. Overall tone? 2. Mixed signals? 3. Confidence? Then provide JSON.
```

**Results**:
| Provider | Output | Format OK? | Accurate? |
|----------|--------|------------|-----------|
| OpenAI   | *[paste]* | | |
| Anthropic | *[paste]* | | |
| Gemini   | *[paste]* | | |

### Best Variation: **[TBD]**
**Why**: *[Explain which variation produced the most accurate and well-formatted results]*

---

## Key Findings

1. **[Cross-provider observation]** — *e.g., "All models handled Variation 2 best because..."*
2. **[Format compliance]** — *e.g., "Gemini sometimes wraps JSON in markdown blocks while OpenAI..."*
3. **[Chain-of-thought trade-off]** — *e.g., "V3 improved accuracy on ambiguous text but sometimes leaked reasoning..."*

---

## Learning Summary (Prompt Engineering)

*[Write 2-3 paragraphs about what you learned from https://www.promptingguide.ai/]*

*Focus on: Basic Prompting, Few-Shot Prompting, Chain-of-Thought techniques and how they applied to your experiments above.*
