# Rola pliku: Testy modułu classification: scenariusze poprawnego działania i błędów. Funkcje test_*
# odkrywa i uruchamia pytest.

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Candidate, CandidateCategory, Source
from app.schemas.classification import CandidateClassification
from app.services.classification_service import ClassificationService
from app.services.llm.base import CandidateInput, LLMError


class FakeProvider:
    """Mock LLM provider: no network calls. Fails for titles listed in `fail_titles`."""

    # __init__ inicjalizuje instancję; self odpowiada this, a przekazane zależności są zapamiętywane w
    # jej polach.
    def __init__(self, fail_titles: set[str] | None = None) -> None:
        self.fail_titles = fail_titles or set()
        self.calls: list[CandidateInput] = []

    # async def tworzy korutynę; await czeka na operację asynchroniczną i pozwala pętli zdarzeń
    # obsługiwać inne zadania.
    async def classify_candidate(self, candidate: CandidateInput) -> CandidateClassification:
        self.calls.append(candidate)
        if candidate.title in self.fail_titles:
            raise LLMError("API down")
        return CandidateClassification(
            relevance=90,
            freshness=80,
            search_potential=70,
            commercial_potential=60,
            category=CandidateCategory.RELEASE,
            reason="Nowy model, duże zainteresowanie.",
        )


async def add_candidate(session: AsyncSession, source: Source, title: str, **fields: object) -> Candidate:
    candidate = Candidate(workspace_id=1, 
        source_id=source.id, external_url=f"https://example.com/{title}", title=title, **fields
    )
    session.add(candidate)
    # commit zatwierdza transakcję; samo zmienienie obiektu ORM lub session.add nie oznacza jeszcze
    # trwałego zapisu.
    await session.commit()
    # refresh ponownie odczytuje rekord, w tym wartości nadane przez bazę, np. ID i daty.
    await session.refresh(candidate)
    return candidate


async def test_classify_stores_scores_and_computes_total(session: AsyncSession, source: Source) -> None:
    candidate = await add_candidate(session, source, "model")
    provider = FakeProvider()

    result = await ClassificationService(session, provider).classify(candidate)

    assert provider.calls[0].source == "Test Feed"
    assert result.relevance_score == 90
    assert result.freshness_score == 80
    assert result.search_potential_score == 70
    assert result.commercial_potential_score == 60
    assert result.total_score == 79
    assert result.category == CandidateCategory.RELEASE
    assert result.llm_reason == "Nowy model, duże zainteresowanie."
    assert result.classified_at is not None


async def test_batch_continues_after_llm_error(session: AsyncSession, source: Source) -> None:
    broken = await add_candidate(session, source, "broken")
    ok = await add_candidate(session, source, "ok")
    already = await add_candidate(session, source, "done", total_score=12)

    result = await ClassificationService(session, FakeProvider({"broken"})).classify_pending()

    assert result.processed == 2
    assert result.classified == 1
    assert result.errors == 1

    for item in (broken, ok, already):
        await session.refresh(item)
    assert broken.total_score is None
    assert broken.category is None
    assert ok.total_score == 79
    assert already.total_score == 12  # already classified candidates are not touched


async def test_failed_reclassification_keeps_previous_result(session: AsyncSession, source: Source) -> None:
    candidate = await add_candidate(
        session, source, "broken", total_score=55, relevance_score=60, llm_reason="old"
    )

    try:
        await ClassificationService(session, FakeProvider({"broken"})).classify(candidate)
    except LLMError:
        pass

    await session.refresh(candidate)
    assert candidate.total_score == 55
    assert candidate.llm_reason == "old"


async def test_classify_pending_respects_limit(session: AsyncSession, source: Source) -> None:
    for title in ("a", "b", "c"):
        await add_candidate(session, source, title)

    result = await ClassificationService(session, FakeProvider()).classify_pending(limit=2)

    assert result.processed == 2
    assert result.classified == 2

async def test_classify_records_usage_and_cost(session: AsyncSession, source: Source) -> None:
    from decimal import Decimal
    class UsageProvider(FakeProvider):
        async def classify_candidate(self, candidate: CandidateInput) -> CandidateClassification:
            result = await super().classify_candidate(candidate)
            result._usage = {"model": "gpt-4.1-mini", "input_tokens": 1000, "output_tokens": 200}
            return result
    candidate = await add_candidate(session, source, "usage")
    result = await ClassificationService(session, UsageProvider()).classify(candidate)
    assert result.llm_model == "gpt-4.1-mini"
    assert result.llm_input_tokens == 1000
    assert result.llm_output_tokens == 200
    assert result.estimated_cost_usd == Decimal("0.000720")
