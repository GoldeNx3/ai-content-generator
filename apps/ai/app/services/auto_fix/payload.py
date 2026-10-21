# Rola pliku: Zawężenie wejścia Auto Fix dla LLM: tylko fakty i źródła związane z poprawianymi issues (czysta funkcja).

import re
from copy import deepcopy


def llm_payload(payload):
    data=deepcopy(payload)
    ids={i for issue in data['issues'] for i in issue['fact_ids']}
    ids.update(data['brief'].get('required_facts',[]))
    ids.update(data['article'].get('lead_fact_ids',[]))
    headings={i.get('section_heading') for i in data['issues']}
    for section in data['article'].get('sections',[]):
        if section.get('heading') in headings: ids.update(section.get('used_fact_ids',[]))
    terms=set(re.findall(r'\w{4,}', ' '.join(i.get('excerpt','')+' '+i.get('suggestion','') for i in data['issues']).casefold()))
    for fact in data['research']['facts']:
        if len(terms & set(re.findall(r'\w{4,}',fact['claim'].casefold()))) >= 2: ids.add(fact['id'])
    data['research']['facts']=[f for f in data['research']['facts'] if f['id'] in ids]
    source_ids={s for f in data['research']['facts'] for s in f.get('source_ids',[])}
    source_ids.update(s for issue in data['issues'] for s in issue.get('source_ids',[]))
    data['research']['sources']=[s for s in data['research']['sources'] if s['id'] in source_ids]
    # Stored facts are short and needed to find a unique replacement when QA has no evidence IDs.
    # Source bodies are omitted; no new retrieval, complete uncertainties/conflicts retained.
    data['research']['sources']=[{k:v for k,v in s.items() if k!='content'} for s in data['research']['sources']]
    data['article']={k:v for k,v in data['article'].items() if k not in ('sections','lead_fact_ids')}
    return data
