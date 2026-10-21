# Rola pliku: Etap classify — oceny i kategoria jednego wpisu.
# Pozostałe etapy nie są potrzebne do klasyfikacji. Wspólny klient odpowiada
# za HTTP i walidację; ta klasa wybiera wyłącznie prompt i schemat klasyfikacji.

from app.schemas.classification import CandidateClassification
from app.services.llm.base import CandidateInput
from app.services.llm.client import OpenAIClient
from app.services.llm.prompt import CLASSIFIER_SYSTEM_PROMPT, build_user_prompt


class OpenAIClassifier:
    """Dostawca spełniający kontrakt LLMProvider z base.py."""

    def __init__(self, client: OpenAIClient, model: str) -> None:
        self.client = client
        self.model = model

    # async def tworzy korutynę; await czeka na operację asynchroniczną i pozwala pętli zdarzeń
    # obsługiwać inne zadania.
    async def classify_candidate(self, candidate: CandidateInput) -> CandidateClassification:
        parsed, usage = await self.client.parse(
            self.model, CLASSIFIER_SYSTEM_PROMPT, build_user_prompt(candidate), CandidateClassification
        )
        # Prywatne metadane tokenów nie należą do schematu odpowiedzi LLM.
        # Wykorzysta je ClassificationService przy zapisywaniu kosztu.
        parsed._usage = {"model": usage.model, "input_tokens": usage.input_tokens, "output_tokens": usage.output_tokens, "response_id": usage.response_id} if usage.recorded else None
        return parsed
