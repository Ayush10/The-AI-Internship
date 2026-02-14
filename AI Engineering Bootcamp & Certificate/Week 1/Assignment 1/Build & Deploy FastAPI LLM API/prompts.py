SUMMARIZE_PROMPTS = {
    1: (
        "Summarize the following text in {max_length} words or fewer. "
        "Return only the summary, nothing else.\n\n"
        "Text:\n{text}"
    ),
    2: (
        "You are an expert summarizer. Read the following text carefully "
        "and produce a concise summary.\n\n"
        "Rules:\n"
        "- Maximum {max_length} words\n"
        "- Capture the main idea and key supporting points\n"
        "- Use clear, simple language\n"
        "- Do not add information not present in the original text\n\n"
        "Text:\n{text}\n\n"
        "Summary:"
    ),
    3: (
        "Read the following text. First, identify the 2-3 most important points. "
        "Then, write a summary of no more than {max_length} words that covers those points.\n\n"
        "Text:\n{text}\n\n"
        "Important points and summary:"
    ),
}

DEFAULT_SUMMARIZE_PROMPT = 2


SENTIMENT_PROMPTS = {
    1: (
        "Analyze the sentiment of the following text. "
        "Respond with ONLY a JSON object in this exact format, no other text:\n"
        '{{"sentiment": "positive" or "negative" or "neutral", '
        '"confidence": 0.0 to 1.0, "explanation": "brief explanation"}}\n\n'
        "Text:\n{text}"
    ),
    2: (
        "You are a sentiment analysis expert. Analyze the sentiment of the given text.\n\n"
        "Classify the sentiment as exactly one of: positive, negative, neutral.\n"
        "Rate your confidence from 0.0 (uncertain) to 1.0 (certain).\n"
        "Provide a one-sentence explanation.\n\n"
        "Return your analysis as a JSON object with keys: "
        '"sentiment", "confidence", "explanation".\n\n'
        "Example output:\n"
        '{{"sentiment": "positive", "confidence": 0.85, '
        '"explanation": "The text expresses enthusiasm and satisfaction."}}\n\n'
        "Text to analyze:\n{text}"
    ),
    3: (
        "Analyze the sentiment of the text below. Think through it step by step:\n\n"
        "1. What is the overall tone of the text?\n"
        "2. Are there any mixed signals or conflicting sentiments?\n"
        "3. How confident are you in your assessment?\n\n"
        "Text:\n{text}\n\n"
        "Now provide your final analysis as a JSON object with exactly these keys:\n"
        '- "sentiment": one of "positive", "negative", or "neutral"\n'
        '- "confidence": a float between 0.0 and 1.0\n'
        '- "explanation": a one-sentence explanation\n\n'
        "JSON:"
    ),
}

DEFAULT_SENTIMENT_PROMPT = 2


CHAT_SYSTEM_PROMPTS = {
    "general": (
        "You are a helpful AI assistant. Respond clearly and concisely."
    ),
    "summarize": (
        "You are a text summarization assistant. When the user sends text, "
        "provide a clear, concise summary capturing the key points. "
        "If the user asks questions, help them with summarization tasks."
    ),
    "sentiment": (
        "You are a sentiment analysis assistant. When the user sends text, "
        "analyze its sentiment (positive, negative, or neutral), provide a "
        "confidence score from 0.0 to 1.0, and explain your reasoning. "
        "If the user asks questions, help them understand sentiment analysis."
    ),
}


ENHANCE_PROMPT_SYSTEM = """You are a prompt engineering expert. Your job is to take a user's raw prompt and enhance it using established prompt engineering principles.

Apply these techniques from promptingguide.ai where relevant:

1. **Specificity**: Make the prompt more specific and detailed. Add constraints, context, and desired output format.
2. **Role Prompting**: If appropriate, assign an expert role (e.g., "You are a senior data scientist...").
3. **Structure**: Add clear structure — numbered steps, bullet points, or sections.
4. **Few-Shot Cues**: If the task would benefit from examples, add 1-2 brief examples of desired input/output.
5. **Chain-of-Thought**: For reasoning or analysis tasks, add "Think step by step" or similar scaffolding.
6. **Output Format**: Specify the desired format (JSON, markdown, bullet points, etc.).
7. **Constraints**: Add relevant constraints (length, tone, audience, what to avoid).

Rules:
- Keep the enhanced prompt's intent identical to the original
- Don't over-engineer simple prompts — apply only the techniques that genuinely help
- Return ONLY the enhanced prompt text, nothing else
- Do not wrap the enhanced prompt in quotes or code blocks

Respond with a JSON object:
{"enhanced_prompt": "the improved prompt text", "techniques_applied": ["technique1", "technique2"]}"""
