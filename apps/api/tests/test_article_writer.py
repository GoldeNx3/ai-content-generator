# Rola pliku: Testy modułu article_writer: scenariusze poprawnego działania i błędów. Funkcje test_*
# odkrywa i uruchamia pytest.

from decimal import Decimal

import pytest
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Article, ArticleStatus, CandidateCategory, ResearchStatus
from app.schemas.article import ArticleBrief, ArticleLength, ArticleUpdate, GenerateArticleRequest
from app.services.article.article_service import ArticleService, ResearchNotReadyError
from app.services.article.article_types import resolve_length
from app.services.article.composition import count_words, slugify
from app.services.article.validation import unsupported_numbers
from app.services.llm.base import LLMError
from app.services.llm.cost import LLMCostCalculator
from tests.article_fakes import FakeArticleLLM, make_brief, make_output, research_fixture

PRICING = {"gpt-4.1-mini": {"input": 0.40, "output": 1.60}, "gpt-4.1": {"input": 2.0, "output": 8.0}}


def service(session: AsyncSession, llm: FakeArticleLLM) -> ArticleService:
    return ArticleService(session, llm, LLMCostCalculator(PRICING))


# async def tworzy korutynę; await czeka na operację asynchroniczną i pozwala pętli zdarzeń obsługiwać
# inne zadania.
async def test_generates_draft_from_research(session: AsyncSession) -> None:
    candidate, research = await research_fixture(session)
    llm = FakeArticleLLM()

    article = await service(session, llm).generate(candidate.id, GenerateArticleRequest())

    fact_ids = [fact.id for fact in research.facts]
    official, news = research.sources[0].id, research.sources[1].id
    # Writer only sees completed research material; failed sources are not offered.
    context = llm.contexts[0]
    assert [f.id for f in context.facts] == fact_ids
    assert {s.id for s in context.sources} == {official, news}
    assert context.uncertainties == [{"claim": "Koszt wdrożenia", "reason": "Brak danych"}]

    assert article.status == ArticleStatus.DRAFT
    assert article.version == 1 and article.is_current
    assert article.article_type == CandidateCategory.NEWS  # candidate category, not the LLM's suggestion
    assert llm.briefs[0].article_type == CandidateCategory.NEWS
    assert llm.briefs[0].desired_length_words == 150 + 45 * 3  # capped by available facts
    assert article.slug == "barclays-rozszerza-wdrozenie-claude"
    assert article.content.startswith("## Co się wydarzyło\n\nBank rozszerza")
    assert "## Claude Code dla programistów" in article.content
    assert article.content.rstrip().endswith("Bank stawia na AI.")
    assert article.generated_content == article.content
    assert article.word_count == count_words(article.lead, article.content)
    assert article.sections_count == 2
    assert article.facts_used_count == 2
    assert article.facts_available_count == 3
    assert article.source_count == 2  # official + news (news via fact #1)
    assert article.sections[0]["source_ids"] == [official, news]
    assert article.sections[1]["source_ids"] == [official]  # filled from the fact's sources
    assert article.research_snapshot["facts"][0]["claim"] == research.facts[0].claim

    # Costs: brief (gpt-4.1-mini) and writer (gpt-4.1) stored separately, article shows the sum.
    assert article.brief_cost_usd == Decimal("0.001600")
    assert article.writer_cost_usd == Decimal("0.026000")
    assert article.estimated_cost_usd == Decimal("0.027600")
    assert article.llm_input_tokens == 7_000 and article.llm_output_tokens == 2_500
    assert article.llm_model == "gpt-4.1"
    # The fake draft is tiny compared to the target, so only the "too short" warning is expected.
    assert len(article.validation_warnings) == 1 and "słów przy celu" in article.validation_warnings[0]


async def test_requires_completed_research(session: AsyncSession) -> None:
    candidate, _ = await research_fixture(session, status=ResearchStatus.FAILED)

    with pytest.raises(ResearchNotReadyError, match="Complete research"):
        await service(session, FakeArticleLLM()).generate(candidate.id, GenerateArticleRequest())


async def test_requires_research(session: AsyncSession, source) -> None:  # type: ignore[no-untyped-def]
    from app.models import Candidate

    candidate = Candidate(source_id=source.id, external_url="https://x.example/a", title="No research")
    session.add(candidate)
    # commit zatwierdza transakcję; samo zmienienie obiektu ORM lub session.add nie oznacza jeszcze
    # trwałego zapisu.
    await session.commit()

    with pytest.raises(ResearchNotReadyError):
        await service(session, FakeArticleLLM()).generate(candidate.id, GenerateArticleRequest())


async def test_llm_failure_creates_nothing(session: AsyncSession) -> None:
    candidate, _ = await research_fixture(session)

    with pytest.raises(LLMError):
        await service(session, FakeArticleLLM(fail_writer=True)).generate(candidate.id, GenerateArticleRequest())

    assert await session.scalar(select(func.count(Article.id))) == 0


async def test_rejects_unknown_fact_and_source_ids(session: AsyncSession) -> None:
    candidate, research = await research_fixture(session)
    fact_ids = [fact.id for fact in research.facts]
    official = research.sources[0].id
    broken = research.sources[2].id  # exists in research, but was never fetched -> not citable

    def output(_ctx):  # type: ignore[no-untyped-def]
        out = make_output(fact_ids, [official])
        out.sections[0].used_fact_ids = [fact_ids[0], 99999]
        out.sections[0].source_ids = [official, 88888, broken]
        out.sections[1].used_fact_ids = [77777]
        out.lead_fact_ids = [66666]
        return out

    llm = FakeArticleLLM(brief=lambda ctx: make_brief(fact_ids, extra_ids=[55555]), output=output)
    article = await service(session, llm).generate(candidate.id, GenerateArticleRequest())

    assert article.sections[0]["used_fact_ids"] == [fact_ids[0]]
    assert broken not in article.sections[0]["source_ids"] and 88888 not in article.sections[0]["source_ids"]
    assert article.sections[1]["used_fact_ids"] == []
    assert article.lead_fact_ids == []
    assert article.brief["required_facts"] == fact_ids[:2]
    assert article.facts_used_count == 1
    warnings = " | ".join(article.validation_warnings)
    assert "99999" in warnings and "77777" in warnings and "66666" in warnings
    assert "88888" in warnings and str(broken) in warnings
    assert "55555" in warnings  # brief referenced a non-existing fact
    assert "nie wskazuje żadnego faktu" in warnings


async def test_numbers_without_facts_are_flagged(session: AsyncSession) -> None:
    candidate, research = await research_fixture(session)
    fact_ids = [fact.id for fact in research.facts]

    def output(ctx):  # type: ignore[no-untyped-def]
        out = make_output(fact_ids, [s.id for s in ctx.sources])
        out.sections[1].content = "Do końca 2026 roku 50% programistów, a koszt wyniesie 12,5 mln funtów."
        return out

    article = await service(session, FakeArticleLLM(output=output)).generate(candidate.id, GenerateArticleRequest())

    assert any("12.5" in w for w in article.validation_warnings)
    assert not any("2026" in w or "50" in w.split(":")[-1].split(", ") for w in article.validation_warnings)


async def test_regenerate_keeps_previous_versions(session: AsyncSession) -> None:
    candidate, _ = await research_fixture(session)
    svc = service(session, FakeArticleLLM())
    first = await svc.generate(
        candidate.id, GenerateArticleRequest(article_type=CandidateCategory.RELEASE, instructions="Krócej")
    )

    second = await svc.regenerate(first.id, GenerateArticleRequest(length=ArticleLength.SHORT))

    versions = await svc.list_versions(candidate.id)
    assert [v.version for v in versions] == [2, 1]
    assert [v.is_current for v in versions] == [True, False]
    assert second.article_type == CandidateCategory.RELEASE  # inherited option
    assert second.generation_options["instructions"] == "Krócej"
    assert second.generation_options["length"] == "short"
    # refresh ponownie odczytuje rekord, w tym wartości nadane przez bazę, np. ID i daty.
    await session.refresh(first)
    assert first.content  # previous draft untouched


async def test_manual_edit_and_status(session: AsyncSession) -> None:
    candidate, _ = await research_fixture(session)
    svc = service(session, FakeArticleLLM())
    article = await svc.generate(candidate.id, GenerateArticleRequest())

    edited = await svc.update(article.id, ArticleUpdate(content="## Nowa sekcja\n\nJeden dwa trzy cztery."))
    assert edited.is_edited
    assert edited.generated_content != edited.content
    assert edited.word_count == count_words(edited.lead, edited.content)

    reviewed = await svc.set_status(article.id, ArticleStatus.REVIEW)
    assert reviewed.status == ArticleStatus.REVIEW


def test_brief_structured_output_validation() -> None:
    # model_dump zamienia model Pydantic na słownik; exclude_unset pomija pola, których użytkownik nie
    # przesłał.
    base = make_brief([1, 2]).model_dump()
    with pytest.raises(ValidationError):
        ArticleBrief.model_validate({**base, "article_type": "gossip"})
    with pytest.raises(ValidationError):
        ArticleBrief.model_validate({**base, "desired_length_words": 50_000})
    with pytest.raises(ValidationError):
        ArticleBrief.model_validate({**base, "required_facts": ["fact one"]})


def test_length_resolution() -> None:
    assert resolve_length(CandidateCategory.NEWS, ArticleLength.AUTO, 300, 20) == 600
    assert resolve_length(CandidateCategory.NEWS, ArticleLength.AUTO, 5000, 20) == 1050  # 150 + 45 * 20
    assert resolve_length(CandidateCategory.NEWS, ArticleLength.AUTO, 5000, 40) == 1200  # type max
    assert resolve_length(CandidateCategory.GUIDE, ArticleLength.LONG, 0, 3) == 285  # facts cap wins
    assert resolve_length(CandidateCategory.COMPARISON, ArticleLength.SHORT, 0, 50) == 1500


def test_helpers() -> None:
    assert slugify("Zażółć gęślą jaźń: GPT-6!") == "zazolc-gesla-jazn-gpt-6"
    assert unsupported_numbers("Cena 20 USD, 3 modele, wersja 4.1 i 3,5x", ["20 dolarów", "GPT-4.1", "3.5 razy"]) == []
    assert unsupported_numbers("Wzrost o 37%", ["Wzrost o 35%"]) == ["37"]

    from app.services.article.validation import suspicious_phrases

    assert suspicious_phrases("Wdrożenie ma na celu poprawę. Warto zauważyć, że...", ["fakt"]) == [
        "ma na celu", "warto zauważyć"
    ]
    assert suspicious_phrases("Program ma na celu X", ["Program ma na celu X"]) == []


def test_inline_markers_are_stripped_and_merged() -> None:
    from app.services.article.composition import sanitize_output

    out = make_output([1, 2], [5])
    out.sections[0].content = "Bank rozszerza współpracę [FACT #1]. Ma 16 000 pracowników (FACT #11, #12) [SOURCE #5]."
    out.lead = "Lead [FACT #2]"

    clean = sanitize_output(out)

    assert clean.sections[0].content == "Bank rozszerza współpracę. Ma 16 000 pracowników."
    assert clean.sections[0].used_fact_ids == [1, 1, 11, 12]
    assert clean.lead == "Lead"
    assert clean.lead_fact_ids == [1, 2]


def test_trim_does_not_leave_dangling_words() -> None:
    from app.services.article.composition import trim_text

    assert trim_text("Barclays wdraża AI Claude globalnie, rozszerzając współpracę z Anthropic", 62) == (
        "Barclays wdraża AI Claude globalnie, rozszerzając współpracę"
    )
    assert trim_text("Krótki tytuł", 70) == "Krótki tytuł"
