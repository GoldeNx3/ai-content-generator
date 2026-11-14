# Rola pliku: Wektory znaczenia (embeddingi) tekstów przez OpenAI; używane do grupowania podobnych tematów.

from dataclasses import asdict

from app.services.llm.base import LLMUsage
from app.services.llm.client import OpenAIClient

DIMENSIONS = 1536


class EmbedResult:
    def __init__(self, vectors: list[list[float]], usage: LLMUsage) -> None:
        self.vectors = vectors
        self._usage = asdict(usage)


class OpenAIEmbedder:
    def __init__(self, client: OpenAIClient, model: str) -> None:
        self.client = client
        self.model = model

    async def embed(self, texts: list[str]) -> EmbedResult:
        response = await self.client._client.embeddings.create(model=self.model, input=texts, dimensions=DIMENSIONS)
        vectors = [item.embedding for item in sorted(response.data, key=lambda item: item.index)]
        return EmbedResult(vectors, LLMUsage(self.model, response.usage.prompt_tokens, 0))
