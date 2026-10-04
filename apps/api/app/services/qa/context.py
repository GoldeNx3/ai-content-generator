"""Frozen QA input and edit detection. Never fetches evidence from the web."""
import hashlib
import json
from copy import deepcopy

from app.services.jobs.errors import JobInputError

FIELDS = ('title', 'slug', 'lead', 'content', 'meta_title', 'meta_description', 'lead_fact_ids', 'sections')


def build_qa_payload(article, include_seo=True):
    snapshot = article.research_snapshot or {}
    if not snapshot.get('facts') or not snapshot.get('sources'):
        raise JobInputError('Ta wersja artykułu nie ma kompletnego snapshotu researchu.', 409)
    # Legacy snapshots were produced by the writer for this article's candidate.
    if snapshot.get('candidate_id', article.candidate_id) != article.candidate_id:
        raise JobInputError('Snapshot researchu należy do innego tematu.', 409)
    if article.research_id is not None and snapshot.get('research_id', article.research_id) != article.research_id:
        raise JobInputError('Snapshot researchu ma nieprawidłowe powiązanie z artykułem.', 409)
    fields = (*FIELDS, "seo_data") if include_seo and article.seo_data else FIELDS
    return deepcopy(dict(article_id=article.id, article_version=article.version,
        candidate_id=article.candidate_id, research_id=article.research_id,
        article={name: getattr(article, name) for name in fields}, brief=article.brief,
        research=snapshot))


def input_hash(payload):
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False,
                                   separators=(',', ':')).encode()).hexdigest()


def matches_article(report, article):
    try:
        return report.input_hash == input_hash(build_qa_payload(article, include_seo="seo_data" in report.input_snapshot.get("article", {})))
    except JobInputError:
        return False
