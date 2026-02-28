from abc import ABC, abstractmethod
from fastapi import HTTPException
import config


class LLMProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str, max_tokens: int = 1024) -> str: ...

    @abstractmethod
    def generate_with_system(self, system: str, prompt: str, max_tokens: int = 1024) -> str: ...


class AnthropicProvider(LLMProvider):
    def __init__(self):
        if not config.ANTHROPIC_API_KEY:
            raise HTTPException(400, "ANTHROPIC_API_KEY is not configured")
        import anthropic
        self.client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

    def generate(self, prompt: str, max_tokens: int = 1024) -> str:
        message = self.client.messages.create(
            model="claude-sonnet-4-5-20250514",
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text

    def generate_with_system(self, system: str, prompt: str, max_tokens: int = 1024) -> str:
        message = self.client.messages.create(
            model="claude-sonnet-4-5-20250514",
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text


class OpenAIProvider(LLMProvider):
    def __init__(self):
        if not config.OPENAI_API_KEY:
            raise HTTPException(400, "OPENAI_API_KEY is not configured")
        from openai import OpenAI
        self.client = OpenAI(api_key=config.OPENAI_API_KEY)

    def generate(self, prompt: str, max_tokens: int = 1024) -> str:
        completion = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
        )
        return completion.choices[0].message.content

    def generate_with_system(self, system: str, prompt: str, max_tokens: int = 1024) -> str:
        completion = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            max_tokens=max_tokens,
        )
        return completion.choices[0].message.content


class GeminiProvider(LLMProvider):
    def __init__(self):
        if not config.GOOGLE_API_KEY:
            raise HTTPException(400, "GOOGLE_API_KEY is not configured")
        from google import genai
        self.client = genai.Client(api_key=config.GOOGLE_API_KEY)

    def generate(self, prompt: str, max_tokens: int = 1024) -> str:
        response = self.client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
        )
        return response.text

    def generate_with_system(self, system: str, prompt: str, max_tokens: int = 1024) -> str:
        from google.genai import types
        response = self.client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system,
            ),
        )
        return response.text


PROVIDERS = {
    "anthropic": AnthropicProvider,
    "openai": OpenAIProvider,
    "gemini": GeminiProvider,
}


def get_provider(name: str) -> LLMProvider:
    cls = PROVIDERS.get(name)
    if cls is None:
        raise HTTPException(400, f"Unknown provider: {name}. Choose from: {list(PROVIDERS.keys())}")
    return cls()
