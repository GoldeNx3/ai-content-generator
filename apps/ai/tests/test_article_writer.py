# Rola pliku: Testy modułu article_writer: scenariusze poprawnego działania i błędów. Funkcje test_*
# odkrywa i uruchamia pytest.

from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.enums import ArticleStatus, CandidateCategory, ResearchStatus
from app.schemas.article import ArticleBrief, ArticleLength, ArticleUpdate, GenerateArticleRequest
from app.services.article.article_types import resolve_length
from app.services.article.composition import count_words, slugify
from app.services.article.validation import unsupported_numbers
from app.services.llm.base import LLMError
from app.services.llm.cost import LLMCostCalculator
from tests.article_fakes import FakeArticleLLM, make_brief, make_output

PRICING = {"gpt-4.1-mini": {"input": 0.40, "output": 1.60}, "gpt-4.1": {"input": 2.0, "output": 8.0}}


# async def tworzy korutynę; await czeka na operację asynchroniczną i pozwala pętli zdarzeń obsługiwać
# inne zadania.


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
    assert resolve_length(CandidateCategory.NEWS, ArticleLength.AUTO, 300, 20) == 300
    assert resolve_length(CandidateCategory.NEWS, ArticleLength.AUTO, 5000, 20) == 1200
    assert resolve_length(CandidateCategory.NEWS, ArticleLength.AUTO, 5000, 40) == 1200  # type max
    assert resolve_length(CandidateCategory.GUIDE, ArticleLength.LONG, 600, 3) == 2500
    assert resolve_length(CandidateCategory.COMPARISON, ArticleLength.SHORT, 1500, 50) == 400


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
