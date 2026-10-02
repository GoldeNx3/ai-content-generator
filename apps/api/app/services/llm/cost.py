from decimal import ROUND_HALF_UP, Decimal

TOKENS_PER_PRICE_UNIT = Decimal(1_000_000)


class LLMCostCalculator:
    """Estimates USD cost from token usage. Prices (USD / 1M tokens) come from configuration."""

    def __init__(self, pricing: dict[str, dict[str, float]]) -> None:
        self._pricing = {model.lower(): prices for model, prices in pricing.items()}

    def estimate(self, model: str, input_tokens: int, output_tokens: int) -> Decimal | None:
        prices = self._prices_for(model)
        if prices is None:
            return None
        cost = (
            Decimal(input_tokens) * Decimal(str(prices["input"]))
            + Decimal(output_tokens) * Decimal(str(prices["output"]))
        ) / TOKENS_PER_PRICE_UNIT
        return cost.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)

    def _prices_for(self, model: str) -> dict[str, float] | None:
        name = model.lower()
        if name in self._pricing:
            return self._pricing[name]
        # Dated snapshots, e.g. "gpt-4.1-mini-2025-04-14" -> "gpt-4.1-mini" (longest prefix wins).
        matches = [key for key in self._pricing if name.startswith(f"{key}-")]
        return self._pricing[max(matches, key=len)] if matches else None
