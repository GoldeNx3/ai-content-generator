"""QA orchestration with durable reports and fenced worker publication."""
import logging
import time

from sqlalchemy import select

from app.models import ArticleStatus, Article, ArticleQA, ArticleQAIssue
from app.schemas.qa import QAOutput
from app.services.jobs.errors import JobInputError
from app.services.jobs.transactions import save, stage
from app.services.qa.context import build_qa_payload, input_hash, matches_article
from app.services.qa.validation import calculate_scores, validate_output, validate_references

logger = logging.getLogger(__name__)


class ArticleQAService:
    def __init__(self, session, llm, cost_calculator, execution=None, settings=None, report=None):
        from app.core.config import get_settings
        self.session, self.llm, self.costs = session, llm, cost_calculator
        self.execution = execution
        self.settings = settings or get_settings()
        self.report = report

    async def evaluate(self, article_id: int) -> ArticleQA:
        article = await self.session.get(Article, article_id)
        if article is None:
            raise JobInputError('Article not found', 404)
        report = self.report
        if report is None:
            payload = build_qa_payload(article)
            report = ArticleQA(article_id=article.id, article_version=article.version,
                input_snapshot=payload, input_hash=input_hash(payload), pass_score=self.settings.qa_pass_score,
                issues=[])
            self.session.add(report)
        payload = report.input_snapshot
        report.status = 'running'
        await save(self.session, self.execution)
        started = time.perf_counter()
        await stage(self.execution, 'validating_references')
        from app.services.article.readability import readability_issues
        reference_issues = validate_references(payload) + readability_issues(payload["article"]["lead"],payload["article"]["content"])
        result = await self.llm.evaluate(payload)
        report.llm_model = result.usage.model
        report.llm_input_tokens = result.usage.input_tokens if result.usage.recorded else None
        report.llm_output_tokens = result.usage.output_tokens if result.usage.recorded else None
        report.estimated_cost_usd = self.costs.estimate(result.usage.model, result.usage.input_tokens,
            result.usage.output_tokens) if result.usage.recorded else None
        # Preserve known usage even if later semantic output validation fails.
        await save(self.session, self.execution)
        await stage(self.execution, 'validating_qa')
        checked = validate_output(QAOutput.model_validate(result.output), payload, reference_issues)
        scores = calculate_scores(checked, report.pass_score)
        for name, value in scores.items():
            setattr(report, name, value)
        report.summary = checked.summary
        report.claims = [claim.model_dump(mode='json') for claim in checked.claims]
        report.issues = [ArticleQAIssue(**issue.model_dump(mode='json')) for issue in checked.issues]
        report.status = 'completed'
        # Lock job first, as final commit does; keep article edit locks short.
        if self.execution:
            await self.execution.lock(self.session)
        with self.session.no_autoflush:
            article = await self.session.scalar(select(Article).where(Article.id == article_id)
                .with_for_update().execution_options(populate_existing=True))
        article.qa_passed = bool(report.qa_passed and matches_article(report, article))
        if article.status not in (ArticleStatus.SUPERSEDED, ArticleStatus.REJECTED):
            if article.qa_passed:
                if article.status != ArticleStatus.APPROVED:
                    article.status = ArticleStatus.READY_FOR_APPROVAL
            else:
                from app.services.auto_fix.context import iterations_used
                used = await iterations_used(self.session, article)
                article.status = ArticleStatus.MANUAL_REVIEW_REQUIRED if used >= self.settings.auto_fix_max_iterations else ArticleStatus.NEEDS_CHANGES
        await save(self.session, self.execution, result=report)
        logger.info('QA completed article_id=%s article_version=%s qa_id=%s job_id=%s model=%s '
            'duration=%.2f issue_count=%s overall_score=%s input_tokens=%s output_tokens=%s cost=%s',
            article.id, article.version, report.id, report.job_id, report.llm_model,
            time.perf_counter()-started, len(report.issues), report.overall_score,
            report.llm_input_tokens, report.llm_output_tokens, report.estimated_cost_usd)
        return report
