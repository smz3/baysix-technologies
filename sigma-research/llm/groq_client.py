"""
Groq LLM client — fast inference (llama-3.3-70b-versatile).

Used for: structured JSON agent outputs, macro classification, regime synthesis.
Falls back to Ollama if GROQ_API_KEY is not set.
"""

import json
import os
from typing import Any

from dotenv import load_dotenv

load_dotenv()


class GroqClient:
    DEFAULT_MODEL = "llama-3.3-70b-versatile"

    def __init__(self):
        self._api_key = os.getenv("GROQ_API_KEY", "")
        self._client = None

    @property
    def is_available(self) -> bool:
        return bool(self._api_key and not self._api_key.startswith("your_"))

    @property
    def client(self):
        if self._client is None:
            from groq import Groq
            self._client = Groq(api_key=self._api_key)
        return self._client

    def chat(self, system: str, user: str, model: str | None = None) -> str:
        if not self.is_available:
            raise RuntimeError("GROQ_API_KEY not configured.")
        model = model or self.DEFAULT_MODEL
        response = self.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.2,
        )
        return response.choices[0].message.content

    def structured_json(self, system: str, user: str, model: str | None = None) -> dict[str, Any]:
        raw = self.chat(system=system, user=user, model=model)
        try:
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            return json.loads(cleaned)
        except (json.JSONDecodeError, IndexError):
            return {"error": "parse_failed", "raw": raw[:500]}


if __name__ == "__main__":
    client = GroqClient()
    if not client.is_available:
        print("GROQ_API_KEY not set — add to .env")
    else:
        result = client.chat(
            system="You are a helpful assistant.",
            user="Say hello in one sentence."
        )
        print(f"Groq response: {result}")
