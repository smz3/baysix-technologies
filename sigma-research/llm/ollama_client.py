"""
Ollama local LLM client.

Connects to Ollama at localhost:11434 for:
- Sentiment classification (qwen2.5:7b)
- Document summarization (qwen2.5:7b)
- Cross-check verification (mistral:7b)

Free, local, GPU-accelerated on RTX 3060+.
"""

import json
import os

from ollama import Client


class OllamaClient:
    """Interface to local Ollama LLM server."""

    DEFAULT_MODEL = "qwen2.5:7b"
    VERIFY_MODEL = "mistral:7b"

    def __init__(self, base_url: str | None = None):
        self._url = base_url or os.getenv("OLLAMA_URL", "http://localhost:11434")
        self._client = None

    @property
    def client(self) -> Client:
        if self._client is None:
            self._client = Client(host=self._url)
        return self._client

    def is_available(self) -> bool:
        """Check if Ollama is running and responsive."""
        try:
            self.client.list()
            return True
        except Exception:
            return False

    def list_models(self) -> list[str]:
        """List available models."""
        try:
            response = self.client.list()
            return [m.model for m in response.models]
        except Exception:
            return []

    def generate(
        self,
        prompt: str,
        model: str | None = None,
        system: str | None = None,
    ) -> str:
        """Generate a response from the local LLM."""
        model = model or self.DEFAULT_MODEL

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = self.client.chat(model=model, messages=messages)
        return response.message.content

    def classify_sentiment(
        self,
        headline: str,
        model: str | None = None,
    ) -> dict:
        """Classify a news headline as bullish/bearish/neutral."""
        system = (
            "You are a financial sentiment classifier. "
            "Respond with ONLY a JSON object: "
            '{"sentiment": "bullish"|"bearish"|"neutral", "confidence": 0.0-1.0, "reason": "brief reason"}'
        )
        prompt = f"Classify the sentiment of this headline:\n\n{headline}"

        raw = self.generate(prompt, model=model, system=system)

        # Try to parse JSON from response
        try:
            # Handle cases where LLM wraps JSON in markdown
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            return json.loads(cleaned)
        except (json.JSONDecodeError, IndexError):
            return {
                "sentiment": "neutral",
                "confidence": 0.0,
                "reason": f"Parse error. Raw: {raw[:100]}",
            }

    def summarize(
        self,
        text: str,
        max_words: int = 100,
        model: str | None = None,
    ) -> str:
        """Summarize a document or text."""
        system = (
            f"Summarize the following text in {max_words} words or less. "
            "Focus on key facts and numbers. Be concise."
        )
        return self.generate(text, model=model, system=system)

    def cross_check(
        self,
        claim: str,
        evidence: str,
        model: str | None = None,
    ) -> dict:
        """Use a different model to verify a claim against evidence."""
        model = model or self.VERIFY_MODEL
        system = (
            "You are a fact-checker. Given a claim and evidence, determine if the claim "
            "is SUPPORTED, CONTRADICTED, or INSUFFICIENT evidence. "
            'Respond with ONLY JSON: {"verdict": "supported"|"contradicted"|"insufficient", "reason": "brief"}'
        )
        prompt = f"Claim: {claim}\n\nEvidence: {evidence}"

        raw = self.generate(prompt, model=model, system=system)

        try:
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            return json.loads(cleaned)
        except (json.JSONDecodeError, IndexError):
            return {
                "verdict": "insufficient",
                "reason": f"Parse error. Raw: {raw[:100]}",
            }


if __name__ == "__main__":
    client = OllamaClient()

    if not client.is_available():
        print("Ollama is not running at localhost:11434")
        print("Start Ollama first, then re-run.")
    else:
        print("Ollama is available!")
        models = client.list_models()
        print(f"Models: {models}")

        if models:
            # Test sentiment classification
            headline = "Fed signals pause in rate hikes as inflation cools"
            print(f"\nClassifying: '{headline}'")
            result = client.classify_sentiment(headline)
            print(f"Result: {result}")
