"""Literal patch application. Nothing outside validated patches is rewritten."""
from copy import deepcopy
from dataclasses import dataclass
from difflib import SequenceMatcher
import re
from app.services.jobs.errors import JobInputError

ALLOWED={'unsupported_claim','title_mismatch','repetition','style_issue','structure_issue','seo_issue','overclaim','too_close_to_source'}
CONDITIONAL={'incorrect_number','incorrect_date'}
NUMBER=re.compile(r'(?<![\w.])\d+(?:[.,]\d+)*')

def eligible(issue):
    return issue.get('auto_fixable',False) and issue['type'] in ALLOWED|CONDITIONAL

@dataclass
class AppliedFix:
    article: dict
    change_ratio: float
    warnings: list[str]
    changes: list[dict]

def apply_fixes(payload,output,threshold):
    issues={i['id']:i for i in payload['issues']}
    results={i.qa_issue_id:i for i in output.fix_results}
    if len(results)!=len(output.fix_results) or set(results)!=set(issues):
        raise JobInputError('Nieprawidłowe lub niekompletne wyniki issue.',422)
    facts={i['id']:i for i in payload['research']['facts']}
    sources={i['id'] for i in payload['research']['sources']}
    original=payload['article'];article=deepcopy(original);edits={};fixed=set();changes=[]
    for patch in output.patches:
        ids=set(patch.qa_issue_ids)
        if not ids<=issues.keys() or not set(patch.fact_ids)<=facts.keys() or not set(patch.source_ids)<=sources:
            raise JobInputError('Auto Fix zwrócił nieistniejące ID.',422)
        if any(not eligible(issues[i]) or results[i].status!='fixed' for i in ids):
            raise JobInputError('Niedozwolona automatyczna poprawka issue.',422)
        def corresponds(issue):
            excerpt = ' '.join(issue.get('excerpt','').split()).casefold()
            before = ' '.join(patch.before.split()).casefold()
            if excerpt and (excerpt in before or before in excerpt): return True
            return issue['type']=='structure_issue' and patch.field=='content'
        if not all(corresponds(issues[i]) for i in ids):
            raise JobInputError('Poprawka nie odpowiada wskazanemu fragmentowi issue.',422)
        if patch.before==patch.after: raise JobInputError('Poprawka fixed musi zmieniać tekst.',422)
        text=original[patch.field]
        if text.count(patch.before)!=1: raise JobInputError('Fragment poprawki nie jest jednoznaczny.',422)
        start=text.index(patch.before);end=start+len(patch.before)
        spans=edits.setdefault(patch.field,[])
        if any(start<b and end>a for a,b,_ in spans): raise JobInputError('Nakładające się poprawki.',422)
        evidence=' '.join(facts[i]['claim'] for i in patch.fact_ids)
        added=set(NUMBER.findall(patch.after))-set(NUMBER.findall(patch.before))
        if added-set(NUMBER.findall(evidence)):
            raise JobInputError('Nowa wartość liczbowa nie ma pokrycia w wskazanych faktach.',422)
        if any(issues[i]['type'] in CONDITIONAL for i in ids) and not patch.fact_ids:
            raise JobInputError('Korekta wartości wymaga jednoznacznego faktu.',422)
        if patch.source_ids and patch.fact_ids and not set(patch.source_ids).intersection({s for i in patch.fact_ids for s in facts[i].get('source_ids',[])}):
            raise JobInputError('Źródła nie wspierają wskazanych faktów.',422)
        spans.append((start,end,patch.after));fixed.update(ids);changes.append(patch.model_dump(mode='json'))
    if {i for i,r in results.items() if r.status=='fixed'}!=fixed:
        raise JobInputError('Wynik fixed nie ma odpowiadającej poprawki.',422)
    for field,spans in edits.items():
        for start,end,after in sorted(spans,reverse=True): article[field]=article[field][:start]+after+article[field][end:]
    for field in ('title','lead','meta_title','meta_description','slug'):
        if not article[field].strip(): raise JobInputError('Poprawka usuwa wymagane pole.',422)
    if len(article['title'])>300 or len(article['meta_title'])>300 or len(article['meta_description'])>500 or len(article['slug'])>300:
        raise JobInputError('Poprawka przekracza limit długości.',422)
    fields=('title','lead','content','slug','meta_title','meta_description')
    before='\n'.join(original[k] for k in fields);after='\n'.join(article[k] for k in fields)
    ratio=1-SequenceMatcher(None,before,after,autojunk=False).ratio()
    warnings=[f'Zakres zmian {ratio:.1%} przekracza próg {threshold:.1%}.'] if ratio>threshold else []
    return AppliedFix(article,ratio,warnings,changes)
