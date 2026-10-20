# Rola pliku: Odtwarzanie metadanych sekcji (fakty, źródła) po zmianie treści artykułu – czysta funkcja.

import re
from difflib import SequenceMatcher


def rebuild_sections(content, previous, research, patches=()):
    from app.services.markdown import fences
    masked=content
    for block in reversed(fences(content)):
        masked=masked[:block.start]+' '* (block.end-block.start)+masked[block.end:]
    headings=list(re.finditer(r'^##[ \t]+(.+)$',masked,re.MULTILINE))
    known_facts={f['id'] for f in research.get('facts',[])}
    known_sources={s['id'] for s in research.get('sources',[])}
    sections=[]
    for index,heading in enumerate(headings):
        text=content[heading.end():headings[index+1].start() if index+1<len(headings) else len(content)].strip()
        name=heading.group(1).strip()
        match=next((s for s in previous if s.get('heading')==name),None)
        if match is None and previous:
            closest=max(previous,key=lambda s:SequenceMatcher(None,s.get('content',''),text,autojunk=False).ratio())
            if SequenceMatcher(None,closest.get('content',''),text,autojunk=False).ratio()>=.6: match=closest
        facts=set(match.get('used_fact_ids',[])) if match else set()
        sources=set(match.get('source_ids',[])) if match else set()
        for patch in patches:
            if patch.field=='content' and ((patch.after and patch.after in text) or (match and patch.before in match.get('content',''))):
                facts.update(patch.fact_ids);sources.update(patch.source_ids)
        sections.append(dict(heading=name,content=text,used_fact_ids=sorted(facts & known_facts),source_ids=sorted(sources & known_sources)))
    return sections
