from abc import ABC, abstractmethod
from fastapi import HTTPException
import config


class LLMProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str, max_tokens: int = 1024) -> str: ...

    @abstractmethod
    def generate_with_system(self, system: str, prompt: str, max_tokens: int = 1024) -> str: ...


class AnthropicProvider(LLMProvider):
    def __init__(self, api_key: str | None = None):
        key = api_key or config.ANTHROPIC_API_KEY
        if not key:
            raise HTTPException(400, "Anthropic API key is not configured. Add your own key in Settings.")
        import anthropic
        self.client = anthropic.Anthropic(api_key=key)

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
    def __init__(self, api_key: str | None = None):
        key = api_key or config.OPENAI_API_KEY
        if not key:
            raise HTTPException(400, "OpenAI API key is not configured. Add your own key in Settings.")
        from openai import OpenAI
        self.client = OpenAI(api_key=key)

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
    def __init__(self, api_key: str | None = None):
        key = api_key or config.GOOGLE_API_KEY
        if not key:
            raise HTTPException(400, "Gemini API key is not configured. Add your own key in Settings.")
        from google import genai
        self.client = genai.Client(api_key=key)

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


def get_provider(name: str, user_keys: dict | None = None) -> LLMProvider:
    cls = PROVIDERS.get(name)
    if cls is None:
        raise HTTPException(400, f"Unknown provider: {name}. Choose from: {list(PROVIDERS.keys())}")
    user_key = (user_keys or {}).get(name)
    return cls(api_key=user_key)
