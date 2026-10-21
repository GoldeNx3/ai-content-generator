# Rola pliku: Testy modułu research_units: scenariusze poprawnego działania i błędów. Funkcje test_*
# odkrywa i uruchamia pytest.

from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.enums import FactBasis, FactImportance, ResearchSourceOrigin, ResearchSourceType
from app.schemas.research import LLMFact, LLMSourceAssessment, ResearchOutput
from app.services.llm.cost import LLMCostCalculator
from app.services.research.content_budget import TRUNCATION_MARKER, fit_documents, truncate_text
from app.services.research.fact_validation import validate_research_output
from app.services.research.source_scoring import apply_llm_suggestion, assess_source, official_domains_for
from app.services.research.urls import normalize_url

OFFICIAL = {"openai.com"}


# parametrize uruchamia ten sam test dla wielu zestawów danych, zamiast powielać jego kod.
@pytest.mark.parametrize(
    ("url", "expected_type", "expected_score"),
    [
        ("https://openai.com/index/gpt-6", ResearchSourceType.OFFICIAL, 100),
        ("https://platform.openai.com/docs/models", ResearchSourceType.DOCUMENTATION, 100),
        ("https://github.com/openai/openai-python", ResearchSourceType.GITHUB, 95),
        ("https://github.com/someone/fork", ResearchSourceType.GITHUB, 65),
        ("https://www.nist.gov/ai", ResearchSourceType.OFFICIAL, 95),
        ("https://www.reuters.com/technology/x", ResearchSourceType.NEWS, 90),
        ("https://techcrunch.com/2026/x", ResearchSourceType.NEWS, 80),
        ("https://someone.medium.com/post", ResearchSourceType.BLOG, 65),
        ("https://www.reddit.com/r/OpenAI/x", ResearchSourceType.COMMUNITY, 50),
        ("https://random-site.io/post", ResearchSourceType.OTHER, 40),
    ],
)
def test_source_scoring(url: str, expected_type: ResearchSourceType, expected_score: int) -> None:
    assessment = assess_source(url, OFFICIAL)
    assert (assessment.source_type, assessment.score) == (expected_type, expected_score)


def test_llm_suggestion_cannot_make_unknown_source_official() -> None:
    unknown = assess_source("https://random-site.io/post", OFFICIAL)
    refined = apply_llm_suggestion(unknown, ResearchSourceType.OFFICIAL)
    assert refined.source_type == ResearchSourceType.OFFICIAL
    assert refined.score == 65

    known = assess_source("https://www.reddit.com/r/x", OFFICIAL)
    assert apply_llm_suggestion(known, ResearchSourceType.OFFICIAL) == known


def test_official_domains_exclude_media() -> None:
    assert official_domains_for("https://www.anthropic.com/news/x") == {"anthropic.com"}
    assert official_domains_for("https://techcrunch.com/x") == set()


def test_normalize_url() -> None:
    assert normalize_url("http://www.Example.com/a/?utm_source=x&id=1#frag") == "https://example.com/a?id=1"


def output(facts: list[LLMFact], **extra: object) -> ResearchOutput:
    return ResearchOutput(
        summary="s", why_it_matters="w", suggested_angle="a", facts=facts,
        uncertainties=[], conflicts=[], source_types=extra.get("source_types", []),  # type: ignore[arg-type]
    )


@pytest.mark.parametrize("confidence", [-1, 101])
def test_fact_confidence_must_be_0_100(confidence: int) -> None:
    with pytest.raises(ValidationError):
        LLMFact(claim="x", importance=FactImportance.CRITICAL, basis=FactBasis.VERIFIABLE, confidence=confidence, source_urls=[])


def test_cost_calculator() -> None:
    calculator = LLMCostCalculator({"gpt-4.1-mini": {"input": 0.40, "output": 1.60}, "gpt-4.1": {"input": 2, "output": 8}})

    assert calculator.estimate("gpt-4.1-mini", 1_000_000, 500_000) == Decimal("1.200000")
    assert calculator.estimate("gpt-4.1-mini-2025-04-14", 1000, 0) == Decimal("0.000400")
    assert calculator.estimate("gpt-4.1-2025-04-14", 1000, 0) == Decimal("0.002000")
    assert calculator.estimate("unknown-model", 1000, 1000) is None


def test_truncation_and_total_budget() -> None:
    text = ("Paragraph sentence. " * 20 + "\n\n") * 20
    truncated = truncate_text(text, 1000)
    assert len(truncated) <= 1000 + len(TRUNCATION_MARKER)
    assert truncated.endswith(TRUNCATION_MARKER)

    fitted = fit_documents([text, text, text], [3000, 2000, 2000], total_budget=4000)
    assert sum(len(item) for item in fitted) <= 4000 + 2 * len(TRUNCATION_MARKER)
    assert len(fitted[0]) > len(fitted[-1])


# async def tworzy korutynę; await czeka na operację asynchroniczną i pozwala pętli zdarzeń obsługiwać
# inne zadania.
async def test_tavily_provider_parses_results() -> None:
    import json

    import httpx

    from app.services.research.search import ManualSearchProvider, TavilySearchProvider

    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json={"results": [{"title": "T", "url": "https://a.com", "content": "snip"}, {"title": "no url"}]})

    # MockTransport przechwytuje HTTP i zwraca odpowiedź z lokalnej funkcji; to wywołanie nie trafia do
    # Internetu.
    provider = TavilySearchProvider("tvly-test", client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    found = await provider.search("gpt-6 api", limit=3)

    assert [(r.title, r.url, r.snippet) for r in found] == [("T", "https://a.com", "snip")]
    assert json.loads(captured[0].content) == {"query": "gpt-6 api", "max_results": 3, "search_depth": "basic"}
    assert await ManualSearchProvider().search("anything") == []
    assert [r.url for r in await ManualSearchProvider(["https://x.com"]).search("q")] == ["https://x.com"]


def test_platform_org_counts_as_official() -> None:
    official = official_domains_for("https://huggingface.co/blog/allenai/astabrief")
    assert official == {"huggingface.co", "allenai"}
    assert assess_source("https://allenai.org/blog/astabrief", official).score == 100
    assert assess_source("https://github.com/allenai/open-instruct", official).score == 95
    assert assess_source("https://openai.com/x", official).source_type == ResearchSourceType.OTHER
    assert official_domains_for("https://huggingface.co/docs/transformers/index") == {"huggingface.co"}
    assert official_domains_for("https://github.com/openai/openai-python") == {"openai"}


def test_sol_pricing_matches_standard_and_long_context() -> None:
    from decimal import Decimal
    from app.core.config import DEFAULT_LLM_PRICING
    from app.services.llm.cost import LLMCostCalculator
    calculator = LLMCostCalculator(DEFAULT_LLM_PRICING)
    assert calculator.estimate("gpt-6.1-sol", 1000, 200) == Decimal("0.004000")
    assert calculator.estimate("gpt-6.1-sol", 300000, 1000) == Decimal("1.215000")
