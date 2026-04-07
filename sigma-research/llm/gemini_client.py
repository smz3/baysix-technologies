"""
Google Gemini client — large-context synthesis and report generation.

Model: gemini-1.5-flash (free tier, 1M token context)
Used for: long-form research reports, multi-document synthesis, P&L narratives.
"""

import os

from dotenv import load_dotenv

load_dotenv()


class GeminiClient:
    DEFAULT_MODEL = "gemini-1.5-flash"

    def __init__(self):
        self._api_key = os.getenv("GEMINI_API_KEY", "")
        self._model = None

    @property
    def is_available(self) -> bool:
        return bool(self._api_key and not self._api_key.startswith("your_"))

    @property
    def model(self):
        if self._model is None:
            import google.generativeai as genai
            genai.configure(api_key=self._api_key)
            self._model = genai.GenerativeModel(self.DEFAULT_MODEL)
        return self._model

    def generate(self, prompt: str) -> str:
        if not self.is_available:
            raise RuntimeError("GEMINI_API_KEY not configured.")
        response = self.model.generate_content(prompt)
        return response.text

    def generate_report(self, context: str, instructions: str) -> str:
        prompt = f"{instructions}\n\n---\n\nCONTEXT DATA:\n{context}"
        return self.generate(prompt)


if __name__ == "__main__":
    client = GeminiClient()
    if not client.is_available:
        print("GEMINI_API_KEY not set — add to .env")
    else:
        result = client.generate("Summarize the current macro environment in 2 sentences.")
        print(f"Gemini response: {result}")
