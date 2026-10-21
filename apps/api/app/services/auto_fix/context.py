from copy import deepcopy
from sqlalchemy import select,func
from app.models import Article,ArticleFix
from app.services.article.versions import latest_qa
from app.services.qa.context import build_qa_payload,matches_article,input_hash
from app.services.auto_fix.validation import eligible
from app.services.jobs.errors import JobInputError

async def iterations_used(session,article):
    ancestors=[];current=article
    while current and current.id not in ancestors:
        ancestors.append(current.id)
        if current.created_by in ('generated','regenerated','legacy'): break
        current=await session.get(Article,current.parent_version_id) if current.parent_version_id else None
    completed=await session.scalar(select(func.max(ArticleFix.iteration)).where(
        ArticleFix.source_article_version_id.in_(ancestors),ArticleFix.status=='completed'))
    return max(article.auto_fix_iteration or 0,completed or 0)

async def prepare_fix(session,article,issue_ids,settings):
    report=await latest_qa(session,article,completed=True)
    if report is None or not matches_article(report,article):
        raise JobInputError('Auto Fix wymaga aktualnego ukończonego QA.')
    iteration=await iterations_used(session,article)+1
    if iteration>settings.auto_fix_max_iterations:
        raise JobInputError('Limit Auto Fix został osiągnięty. Wymagana ręczna weryfikacja.')
    issues={i.id:i for i in report.issues}
    if issue_ids is None: selected=[i for i in issues.values() if i.auto_fixable]
    else:
        if len(set(issue_ids))!=len(issue_ids) or not set(issue_ids)<=issues.keys():
            raise JobInputError('Issue IDs nie należą do QA tej wersji.',422)
        selected=[issues[i] for i in issue_ids]
    data=build_qa_payload(article)
    data['issues']=[{name:getattr(i,name) for name in ('id','type','severity','excerpt','reason','suggestion','section_heading','fact_ids','source_ids','auto_fixable')} for i in selected]
    # Policy is authoritative: the QA model's bool alone is insufficient.
    for i in data['issues']: i['auto_fixable']=eligible(i)
    if not any(i['auto_fixable'] for i in data['issues']):
        raise JobInputError('Brak bezpiecznych issues do Auto Fix.')
    data['qa_id']=report.id;data['iteration']=iteration
    return report,data


from app.services.auto_fix.payload import llm_payload  # noqa: E402,F401 (re-eksport)
