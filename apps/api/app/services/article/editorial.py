"""Recent composition metadata helps vary form without reusing previous factual content."""
import re
from sqlalchemy import select
from app.models import Article
from app.services.markdown import fences, without_fenced_code


def describe_structure(sections: list[dict], content: str) -> dict[str, object]:
    prose = without_fenced_code(content)
    return {
        'headings': [str(s['heading'])[:160] for s in sections[:12] if s.get('heading')],
        'section_count': len(sections),
        'code_blocks': len(fences(content)),
        'tables': len(re.findall(r'^\s*\|?\s*:?-{3,}:?\s*\|.*$', prose, re.MULTILINE)),
        'lists': len(re.findall(r'^(?:[-*+] |\d+\. )', prose, re.MULTILINE)),
    }


async def recent_structures(session) -> list[dict[str, object]]:
    rows = (await session.execute(select(Article.sections, Article.content).where(Article.is_current)
                                  .order_by(Article.created_at.desc(), Article.id.desc()).limit(5))).all()
    return [describe_structure(sections or [], content or '') for sections, content in rows]
