"""Recent composition metadata helps vary form without reusing previous factual content."""
import re
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

