# Rola pliku: Kontekst wykonania zadania AI: ustawienia procesu, tryb demo, dostawcy LLM i rejestr płatnych
# wywołań z kosztem (ten sam kształt co llm_calls w próbach jobów).

from dataclasses import asdict, is_dataclass
from decimal import Decimal

from app.core.config import Settings, get_settings
from app.demo import demo_settings
from app.services.llm.client import OpenAIClient
from app.services.llm.cost import LLMCostCalculator


class TaskContext:
    def __init__(self, demo: bool = False, settings: Settings | None = None) -> None:
        base = settings or get_settings()
        self.demo = demo
        self.settings = Settings(**demo_settings(base.model_dump())) if demo else base
        self.costs = LLMCostCalculator(self.settings.llm_pricing)
        self.calls: list[dict] = []
        self._client: OpenAIClient | None = None
        self._providers: dict | None = None

    @property
    def providers(self) -> dict:
        if self._providers is None:
            if self.demo:
                from app.workers.demo_providers import demo_providers
                self._providers = demo_providers()
            else:
                from app.workers.providers import providers_for
                self._providers = providers_for(self.settings)
                self._client = self._providers.get("_client")
        return self._providers

    @property
    def extractor(self):
        if self.demo:
            return self.providers["extractor"]
        from app.services.research.content_extractor import ContentExtractor
        return ContentExtractor(timeout=self.settings.page_fetch_timeout_seconds, max_bytes=self.settings.page_max_bytes)

    @property
    def search(self):
        if self.demo:
            return self.providers["search"]
        from app.services.research.search import get_search_provider
        return get_search_provider(self.settings)

    async def call(self, stage: str, invoke):
        """Wykonuje płatne wywołanie i zapisuje je; przerwane wywołanie zostaje z nieznanym kosztem."""
        self.calls.append({"stage": stage, "finished": False, "estimated_cost_usd": None})
        result = await invoke()
        usage = getattr(result, "usage", None) or getattr(result, "_usage", None)
        usage = asdict(usage) if is_dataclass(usage) else usage
        cost = None
        if usage and usage.get("recorded", True):
            cost = self.costs.estimate(usage["model"], usage["input_tokens"], usage["output_tokens"])
        self.calls[-1] = {"stage": stage, "finished": True, "usage": usage,
                          "response_id": usage.get("response_id") if usage else None,
                          "estimated_cost_usd": str(cost) if cost is not None else None}
        return result

    def total_cost(self, stages: set[str] | None = None) -> Decimal | None:
        selected = [c for c in self.calls if stages is None or c["stage"] in stages]
        if not selected or any(c["estimated_cost_usd"] is None for c in selected):
            return None
        return sum((Decimal(c["estimated_cost_usd"]) for c in selected), Decimal(0))

    async def close(self) -> None:
        if self._client is not None:
            await self._client._client.close()
