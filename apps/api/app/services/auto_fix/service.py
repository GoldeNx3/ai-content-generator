import logging,time
from copy import deepcopy
from sqlalchemy import select
from app.models import Article,ArticleFix,ArticleFixIssue,Candidate
from app.schemas.auto_fix import FixOutput
from app.services.auto_fix.context import prepare_fix,llm_payload
from app.services.auto_fix.validation import apply_fixes
from app.services.article.versions import child_version,content_hash
from app.services.jobs.transactions import save,stage
from app.services.jobs.errors import JobInputError
from app.services.qa.context import input_hash
logger=logging.getLogger(__name__)

class ArticleAutoFixService:
    def __init__(self,session,llm,cost_calculator,execution=None,settings=None,report=None):
        from app.core.config import get_settings
        self.session,self.llm,self.costs=session,llm,cost_calculator
        self.execution,self.settings,self.report=execution,settings or get_settings(),report

    async def fix(self,article_version_id:int,issue_ids:list[int]|None=None)->ArticleFix:
        article=await self.session.get(Article,article_version_id)
        if not article: raise JobInputError('Article version not found',404)
        report=self.report
        if report is None:
            qa,payload=await prepare_fix(self.session,article,issue_ids,self.settings)
            report=ArticleFix(source_article_version_id=article.id,qa_id=qa.id,input_hash=input_hash(payload),
                input_snapshot=payload,iteration=payload['iteration'],issues_requested=len(payload['issues']),issues=[])
            self.session.add(report)
        payload=report.input_snapshot;report.status='running'
        await save(self.session,self.execution);started=time.perf_counter()
        await stage(self.execution,'fixing_article')
        request_payload=llm_payload(payload)
        result=await self.llm.fix(request_payload)
        report.llm_model=result.usage.model
        report.llm_input_tokens=result.usage.input_tokens if result.usage.recorded else None
        report.llm_output_tokens=result.usage.output_tokens if result.usage.recorded else None
        report.estimated_cost_usd=self.costs.estimate(result.usage.model,result.usage.input_tokens,result.usage.output_tokens) if result.usage.recorded else None
        await save(self.session,self.execution)
        await stage(self.execution,'validating_fix')
        output=FixOutput.model_validate(result.output)
        applied=apply_fixes(request_payload,output,self.settings.auto_fix_max_change_ratio)
        # All final domain writes are fenced and short. Source content is never updated.
        if self.execution: await self.execution.lock(self.session)
        await self.session.scalar(select(Candidate.id).where(Candidate.id==article.candidate_id).with_for_update())
        with self.session.no_autoflush:
            article=await self.session.scalar(select(Article).where(Article.id==article_version_id).with_for_update().execution_options(populate_existing=True))
        if content_hash(article)!=content_hash(payload['article']): raise JobInputError('Wersja źródłowa zmieniła się podczas poprawki.')
        report.issues=[ArticleFixIssue(**r.model_dump()) for r in output.fix_results]
        report.issues_fixed=sum(r.status=='fixed' for r in output.fix_results)
        report.issues_skipped=sum(r.status=='skipped' for r in output.fix_results)
        report.summary=output.summary;report.change_ratio=applied.change_ratio
        report.changes=applied.changes;report.warnings=applied.warnings;report.status='completed'
        changed=any(applied.article[k]!=payload['article'][k] for k in applied.article)
        if changed:
            from app.services.article.versions import rebuild_sections
            sections=rebuild_sections(applied.article['content'],article.sections,article.research_snapshot,output.patches)
            lead_ids=sorted(set(article.lead_fact_ids)|{i for p in output.patches if p.field=='lead' for i in p.fact_ids})
            changes={k:v for k,v in applied.article.items() if k not in ('sections','lead_fact_ids')}
            changes.update(sections=sections,lead_fact_ids=lead_ids)
            child=await child_version(self.session,article,changes,'auto_fix',report.iteration)
            report.result_article_version_id=child.id
        else:
            article.status='manual_review_required'
        await save(self.session,self.execution,result=report)
        logger.info('Auto Fix completed article_id=%s article_version=%s fix_id=%s job_id=%s result_article_id=%s model=%s duration=%.2f fixed=%s skipped=%s change_ratio=%s tokens=%s/%s cost=%s',article.id,article.version,report.id,report.job_id,report.result_article_version_id,report.llm_model,time.perf_counter()-started,report.issues_fixed,report.issues_skipped,report.change_ratio,report.llm_input_tokens,report.llm_output_tokens,report.estimated_cost_usd)
        return report
