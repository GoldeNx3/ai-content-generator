# Rola pliku: Dane researchu i fałszywy dostawca artykułów: testy dostają kontrolowane odpowiedzi bez
# płatnych wywołań LLM.

"""Fixtures and LLM doubles for the article writer (no network, no cost)."""

from collections.abc import Callable


from app.enums import CandidateCategory, FactImportance, FetchStatus, ResearchSourceOrigin, ResearchSourceType, ResearchStatus
from app.schemas.article import ArticleBrief, WriterOutput, WriterSection
from app.services.llm.base import ArticleContext, BriefResult, LLMError, LLMUsage, WriterResult


# async def tworzy korutynę; await czeka na operację asynchroniczną i pozwala pętli zdarzeń obsługiwać
# inne zadania.


def make_brief(fact_ids: list[int], extra_ids: list[int] | None = None) -> ArticleBrief:
    return ArticleBrief(
        article_type=CandidateCategory.RELEASE,  # backend must override with the requested/candidate type
        primary_angle="Barclays wdraża Claude w skali banku",
        target_audience="Programiści i menedżerowie IT",
        suggested_title="Barclays rozszerza wdrożenie Claude",
        key_points=["Rozszerzenie współpracy", "Claude Code dla programistów"],
        required_facts=fact_ids[:2] + (extra_ids or []),
        optional_facts=fact_ids[2:],
        uncertainties_to_avoid=["Koszt wdrożenia"],
        conflicts_to_mention=[],
        desired_length_words=3000,
    )


def make_output(fact_ids: list[int], source_ids: list[int], **overrides: object) -> WriterOutput:
    data: dict[str, object] = {
        "title": "Barclays rozszerza wdrożenie Claude",
        "slug": "Barclays Rozszerza Wdrożenie Claude!",
        "lead": "Barclays rozszerza współpracę z Anthropic.",
        "lead_fact_ids": [fact_ids[0]],
        "sections": [
            WriterSection(
                heading="## Co się wydarzyło",
                content="Bank rozszerza współpracę z Anthropic.",
                used_fact_ids=[fact_ids[0]],
                source_ids=[source_ids[0]],
            ),
            WriterSection(
                heading="Claude Code dla programistów",
                content="Do końca 2026 roku 50% programistów ma używać Claude Code.",
                used_fact_ids=[fact_ids[1]],
                source_ids=[],
            ),
        ],
        "conclusion": "Bank stawia na AI.",
        "conclusion_fact_ids": [],
        "seo_data": {
            "excerpt": "Barclays rozszerza współpracę z Anthropic.",
            "focus_keyword": "Claude Code", "secondary_keywords": ["Barclays", "Anthropic"],
            "tags": ["Claude", "Anthropic", "Barclays"], "category": "Newsy", "schema_type": "NewsArticle",
            "og_title": "Barclays rozszerza wdrożenie Claude", "og_description": "Barclays rozszerza współpracę z Anthropic.",
            "twitter_title": "Barclays rozszerza wdrożenie Claude", "twitter_description": "Barclays rozszerza współpracę z Anthropic.",
        },
        "meta_title": "Barclays rozszerza wdrożenie Claude",
        "meta_description": "Barclays rozszerza współpracę z Anthropic i chce, by połowa programistów używała Claude Code.",
    }
    data.update(overrides)
    return WriterOutput.model_validate(data)


class FakeArticleLLM:
    # __init__ inicjalizuje instancję; self odpowiada this, a przekazane zależności są zapamiętywane w
    # jej polach.
    def __init__(
        self,
        brief: Callable[[ArticleContext], ArticleBrief] | None = None,
        output: Callable[[ArticleContext], WriterOutput] | None = None,
        fail_writer: bool = False,
    ) -> None:
        self._brief = brief or (lambda ctx: make_brief([f.id for f in ctx.facts]))
        self._output = output or (lambda ctx: make_output([f.id for f in ctx.facts], [s.id for s in ctx.sources]))
        self.fail_writer = fail_writer
        self.contexts: list[ArticleContext] = []
        self.briefs: list[ArticleBrief] = []

    async def generate_brief(self, context: ArticleContext) -> BriefResult:
        self.contexts.append(context)
        return BriefResult(self._brief(context), LLMUsage("gpt-4.1-mini", 2_000, 500))

    async def write_article(self, context: ArticleContext, brief: ArticleBrief) -> WriterResult:
        self.briefs.append(brief)
        if self.fail_writer:
            raise LLMError("OpenAI request failed: 500")
        return WriterResult(self._output(context), LLMUsage("gpt-4.1", 5_000, 2_000))
