"""Idempotent synthetic scenarios. No provider, HTTP request or AI call is made."""
import asyncio
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select, text
from app.core.db import SessionLocal
from app.demo import DEMO_PREFIX
from app.models import Article, ArticleFix, ArticleFixIssue, ArticleQA, ArticleQAIssue, Candidate, Research, ResearchFact, ResearchSource, Source
from app.models.job import Job, JobAttempt
from app.schemas.qa import QAOutput
from app.services.article.versions import content_hash
from app.services.qa.context import build_qa_payload, input_hash
from app.services.qa.validation import calculate_scores, validate_output, validate_references
import argparse, sys
from app.jobs.workspace_arg import WorkspaceNotFound, resolve_workspace, workspace_argument

# slug, title, explanation; stable URLs make repeated invocations non-destructive.
CASES = [
    ('discovered', 'Zacznij tutaj — cały interaktywny flow', 'Kliknij ocenę, Research, generowanie, QA, Auto Fix i Approval. Writer celowo dodaje niepoparte 47%; Auto Fix usuwa zdanie, a nowe QA przechodzi. Wszystkie akcje demo są bezpłatne.'),
    ('classified', 'Ocena tematu — gotowy do Research', 'Ocena pomaga wybrać temat. Zatwierdzenie tematu nie jest zatwierdzeniem tekstu. Research można uruchomić także bez klasyfikacji.'),
    ('ignored', 'Temat pominięty', 'Decyzja redakcyjna ignored nie usuwa historii; możesz przywrócić temat do oczekujących.'),
    ('research-queued', 'Research czeka w kolejce', 'Migawka stanu queued: request już zakończony, worker jeszcze nie rozpoczął. To nieruchomy przykład; do klikania wybierz scenariusz 01.'),
    ('research-running', 'Research w toku', 'Migawka running: worker pobiera i analizuje źródła. W demo nie pobiera internetu. Aktywne zadanie blokuje równoległe płatne zadania tego tematu.'),
    ('research-failed', 'Research nieudany — retry', 'Zadanie failed pokazuje błąd i przycisk retry. Ponowienie demo przechodzi przez tę samą kolejkę bez kosztów.'),
    ('research-ready', 'Research gotowy — Brief i Write', 'Fakty mają rzeczywiste ID oraz powiązane źródła. Niepewności i konflikty pozostają jawne. Generowanie wymaga ukończonego Research i faktów.'),
    ('write-queued', 'Generowanie czeka w kolejce', 'Migawka queued. Brief i Write są jednym zadaniem, ale osobnymi etapami modelu; nie ma jeszcze artykułu.'),
    ('brief-running', 'Brief — plan artykułu', 'Migawka building_brief. Brief wybiera kąt, odbiorcę, fakty i plan sekcji; jeszcze nie tworzy gotowego tekstu.'),
    ('write-failed', 'Write nieudany — retry', 'Błąd generowania nie oznacza powstania nowej wersji. Retry ponawia zadanie; poprawne checkpointy ograniczają powtarzanie pracy.'),
    ('draft', 'Draft — QA wymagane', 'Wersja została wygenerowana, ale nie ma raportu QA. Wybór wersji w sekcji QA określa dokładnie analizowany tekst.'),
    ('qa-queued', 'QA w kolejce', 'Migawka pending/queued. Raport powstaje już przy enqueue i jest przypięty do konkretnego ID oraz numeru wersji.'),
    ('qa-running', 'QA w toku', 'Migawka running. QA korzysta tylko ze snapshotu Research i briefu tej wersji, bez nowego researchu.'),
    ('qa-failed', 'QA nieudane — retry', 'Nie ma wiarygodnego wyniku, dopóki raport nie jest completed. Retry tworzy nowe zadanie i nowy raport dla tej samej wersji.'),
    ('qa-clean', 'QA passed — brak Auto Fix', 'Wynik 95, zero critical i unsupported. Wersja ready_for_approval. Auto Fix jest disabled, ponieważ nie ma problemów do poprawienia.'),
    ('qa-unsupported', 'Auto Fix dostępny — niepoparte 47%', 'Niepoparte zdanie jest high unsupported_claim, wynik ograniczony do 75. Auto Fix jest dostępny dzięki auto_fixable, a nie samemu niskiemu wynikowi.'),
    ('qa-quote', 'Niepoparty cytat — manual review', 'Cytat przypisany osobie bez dowodu jest critical. Wynik najwyżej 60. Nie poprawiamy go automatycznie; człowiek musi zweryfikować lub usunąć fragment.'),
    ('qa-date', 'Sprzeczna data', 'Research podaje premierę 1 czerwca 2026; tekst podaje 2025. Sprzeczność critical blokuje approval.'),
    ('qa-number', 'Nieprawidłowa cena — warunkowy Auto Fix', 'Tekst podaje 99 USD, Research jednoznacznie 9,99 USD. Ten incorrect_number jest auto_fixable, bo istnieje poprawna wartość i powiązany fakt.'),
    ('qa-uncertainty', 'Pominięta niepewność', 'Cena Enterprise niepotwierdzona, a tekst traktuje ją jako fakt. Wymagana ręczna weryfikacja; Auto Fix nie zgaduje.'),
    ('qa-conflict', 'Konflikt źródeł', 'Dwa źródła wskazują różne regiony hostingu. Tekst wybiera jedną wersję bez zastrzeżenia. Auto Fix nie rozstrzyga konfliktu.'),
    ('qa-editorial', 'Styl, struktura, tytuł i SEO', 'Pokazuje powtórzenia, generyczny styl, mylący tytuł i metadata. To problemy redakcyjne możliwe do poprawienia bez nowych faktów.'),
    ('qa-references', 'Nieprawidłowe fact/source IDs', 'Backend wykrywa ID spoza snapshotu i zapisuje source_mismatch. Tych relacji nie wolno wymyślać; trzeba sprawdzić materiał.'),
    ('qa-catalog', 'Katalog wszystkich typów issue', 'Wszystkie 16 typów issue i 4 poziomy severity. To katalog edukacyjny, nie realistyczny wynik jednego modelu; część wymaga człowieka.'),
    ('qa-warnings', 'Warnings nie blokują Approval', 'QA 95 i tylko ostrzeżenia redakcyjne. Zero critical i unsupported pozwala zatwierdzić; warning nie musi oznaczać blokady.'),
    ('fix-queued', 'Auto Fix w kolejce', 'Migawka pending/queued. Zapisano wersję wejściową i listę issue. Stara wersja pozostaje bez zmian.'),
    ('fix-running', 'Auto Fix poprawia tekst', 'Migawka running. Aktywne zadanie blokuje drugi Auto Fix dla tego tematu.'),
    ('fix-failed', 'Auto Fix nieudany — retry', 'Zadanie failed i wyniki failed dla issue; nie utworzono częściowej wersji. Możesz ponowić zadanie.'),
    ('fix-skipped', 'Wszystkie poprawki pominięte', 'Brak bezpiecznej poprawki: skipped, bez nowej wersji i bez zbędnego QA. Wymagana ręczna weryfikacja.'),
    ('fix-qa', 'Nowa wersja — QA w kolejce', 'Auto Fix zakończony, v2 istnieje, ale jest draft. QA v1 nie przechodzi na v2. Automatycznie dodane QA v2 jest jeszcze pending.'),
    ('fix-ready', 'Auto Fix zakończony — Approval', 'v1 QA 75 → usunięcie 47% → v2 QA 95. Sprawdź Before/After i koszt 0.00; możesz zatwierdzić konkretnie v2.'),
    ('fix-needs-changes', 'Po poprawce nadal needs_changes', 'Nowe QA nadal wykrywa niepoparte twierdzenie. Pozostała jedna iteracja Auto Fix; następna nie uruchamia się samoczynnie.'),
    ('fix-limit', 'Limit dwóch iteracji', 'v1 → v2 → v3, dwa zakończone Auto Fix. QA nadal nie przechodzi, status manual_review_required i zero pozostałych prób.'),
    ('approved', 'Zatwierdzona konkretna wersja', 'Approved oznacza decyzję człowieka dla tej wersji. Nic nie jest publikowane automatycznie.'),
    ('rejected', 'Wersja odrzucona', 'Reject zapisuje powód i zachowuje historię. Możesz ręcznie edytować tekst, tworząc nową wersję wymagającą QA.'),
    ('superseded', 'Nowe approval zastępuje stare', 'v1 superseded, v2 approved. Tylko jedna wersja tematu jest aktywnie zatwierdzona; obie pozostają w historii.'),
    ('manual-edit', 'Ręczna edycja po QA', 'v1 ma QA i approval; v2 jest nową ręcznie edytowaną wersją draft. QA jest wymagane ponownie, nie wolno dziedziczyć starego wyniku.'),
    ('qa-stale', 'Stary raport — hash nie pasuje', 'Przykład danych legacy z nieaktualnym raportem. UI oznacza stale, blokuje Auto Fix i Approval; uruchom QA dla aktualnego tekstu.'),
    ('queue-retrying', 'Automatyczny retry po błędzie przejściowym', 'Migawka retrying. Worker ponawia błąd przejściowy w ramach tego samego zadania; historia prób i last_error pozostają widoczne. Kolejny Auto Fix nie jest przez to uruchamiany.'),
]
ISSUES = {
    'unsupported_claim': ('high', 'Nexa zwiększa produktywność o 47%.', 'Research nie zawiera wyniku 47%.', 'Usuń niepoparte zdanie.', True),
    'contradiction': ('critical', 'Premiera Nexa odbyła się w 2025.', 'Research wskazuje 1 czerwca 2026.', 'Zweryfikuj datę względem Research.', False),
    'incorrect_number': ('high', 'Nexa Basic kosztuje 99 USD miesięcznie.', 'Potwierdzona cena to 9,99 USD miesięcznie.', 'Zastąp cenę wartością 9,99 USD.', True),
    'incorrect_date': ('high', 'Premiera Nexa przypada na 2 czerwca 2026.', 'Potwierdzona data to 1 czerwca 2026.', 'Użyj daty 1 czerwca 2026.', True),
    'unsupported_quote': ('critical', 'Anna Nowak powiedziała: „Nexa zmienia wszystko”.', 'Research nie zawiera tego cytatu ani potwierdzonego autora.', 'Zweryfikuj cytat ręcznie.', False),
    'unsupported_name': ('high', 'Twórcą Nexa jest Jan Kowalski.', 'Research nie podaje autora o takim nazwisku.', 'Usuń lub zweryfikuj przypisanie.', False),
    'source_mismatch': ('warning', '', 'Nieprawidłowe ID faktu i źródła spoza Research tej wersji.', 'Sprawdź relacje faktów i źródeł.', False),
    'missing_uncertainty': ('high', 'Cena Nexa Enterprise wynosi 100 USD.', 'Cena Enterprise nie została potwierdzona.', 'Nie przedstawiaj ceny jako pewnika.', False),
    'ignored_conflict': ('high', 'Dane Nexa są przechowywane wyłącznie w Europie.', 'Materiały różnią się co do regionu hostingu.', 'Opisz konflikt bez rozstrzygania.', False),
    'title_mismatch': ('warning', 'Nexa gwarantuje podwojenie wyników', 'Tytuł sugeruje nieudowodniony wynik.', 'Dopasuj tytuł do potwierdzonych funkcji.', True),
    'repetition': ('warning', 'Eksport Markdown jest dostępny. Eksport Markdown jest dostępny.', 'Powtórzone zdanie nie wnosi informacji.', 'Usuń powtórzenie.', True),
    'style_issue': ('warning', 'Warto zauważyć. Nie ulega wątpliwości. To pokazuje, jak ważne jest.', 'Nagromadzenie pustych przejść utrudnia lekturę.', 'Usuń generyczne przejścia.', True),
    'structure_issue': ('warning', 'Ta sekcja powtarza lead i nie rozwija tematu.', 'Sekcja nie realizuje planu briefu.', 'Skróć sekcję do istotnych informacji.', True),
    'seo_issue': ('warning', 'Najlepszy produkt z gwarancją wyników', 'Meta description dodaje niepotwierdzoną obietnicę.', 'Opisz wyłącznie potwierdzone funkcje.', True),
    'overclaim': ('high', 'Nexa jest bezkonkurencyjna na całym rynku.', 'Research nie zawiera porównania całego rynku.', 'Usuń nieudowodnioną ocenę.', True),
    'other': ('info', 'Materiał demonstracyjny.', 'Przykład dodatkowej uwagi informacyjnej.', 'Brak wymaganej zmiany.', False),
}

async def _research(session, candidate):
    r = Research(candidate_id=candidate.id, status='completed', summary='Syntetyczny Research: funkcje i cena fikcyjnego Nexa.',
        why_it_matters='Demo sposobu pracy z dowodami.', suggested_angle='Co potwierdzono o Nexa?',
        llm_model='demo-static', llm_input_tokens=0, llm_output_tokens=0, estimated_cost_usd=0, sources=[], facts=[])
    session.add(r); await session.flush()
    for n, region in enumerate(('Europa', 'USA'), 1):
        s = ResearchSource(research_id=r.id, url=DEMO_PREFIX+f'evidence/{candidate.id}/{n}', origin='original' if n==1 else 'manual',
            title=f'Nexa — materiał demo {n}', publisher='Demo Content Engine', source_type='official', source_score=95,
            extracted_content=f'Nexa Studio udostępnia eksport Markdown. Nexa Basic kosztuje 9,99 USD miesięcznie. Premiera: 1 czerwca 2026. Region hostingu: {region}. Cena Enterprise nie została potwierdzona.',
            fetch_status='success', http_status=200)
        r.sources.append(s)
    await session.flush()
    for claim in ('Nexa Studio udostępnia eksport Markdown.', 'Nexa Basic kosztuje 9,99 USD miesięcznie.', 'Premiera Nexa odbyła się 1 czerwca 2026.'):
        r.facts.append(ResearchFact(research_id=r.id, claim=claim, importance='important', confidence=95, sources=[r.sources[0]]))
    await session.flush()
    r.uncertainties=[{'claim':'Cena Enterprise', 'reason':'Cena Enterprise nie została potwierdzona.'}]
    r.conflicts=[{'topic':'Region hostingu', 'sources':[{'url':s.url, 'claim':region} for s,region in zip(r.sources,('Europa','USA'))]}]
    return r

async def _article(session, candidate, research, version=1, parent=None, types=()):
    if parent:
        parent.is_current=False; await session.flush()
    facts=[{'id':f.id,'claim':f.claim,'importance':f.importance,'confidence':f.confidence,'source_ids':f.source_ids} for f in research.facts]
    sources=[{'id':s.id,'url':s.url,'title':s.title,'publisher':s.publisher,'source_type':s.source_type,'source_score':s.source_score,'content':s.extracted_content} for s in research.sources]
    title='Nexa: eksport Markdown i cena Basic'
    section='Nexa Studio udostępnia eksport Markdown. Nexa Basic kosztuje 9,99 USD miesięcznie.'
    for typ in types:
        if typ=='title_mismatch': title=ISSUES[typ][1]
        elif typ!='seo_issue' and ISSUES[typ][1]: section+='\n\n'+ISSUES[typ][1]
    ids=[f.id for f in research.facts[:2]]
    sections=[dict(heading='Funkcje i cena',content=section,used_fact_ids=list(ids),source_ids=[research.sources[0].id])]
    if 'source_mismatch' in types:
        sections[0]['used_fact_ids'] += [99999999]; sections[0]['source_ids'] += [99999998]
    body='## Funkcje i cena\n\n'+section+'\n\n## Co pozostaje niepewne\n\nCena Enterprise nie została potwierdzona. Źródła różnią się co do regionu hostingu.'
    brief=dict(article_type='news',article_format='news',primary_angle='Potwierdzone funkcje Nexa',target_audience='Redaktorzy poznający pipeline',suggested_title=title,
        key_points=[f.claim for f in research.facts],required_facts=ids,optional_facts=[],uncertainties_to_avoid=['Cena Enterprise niepotwierdzona'],conflicts_to_mention=['Region hostingu'],desired_length_words=400,
        section_plan=[dict(heading='Funkcje i cena',purpose='Wyjaśnij fakty z Research.',fact_ids=ids,target_words=200,presentation='prose')],research_gaps=[])
    a=Article(candidate_id=candidate.id,research_id=research.id,version=version,is_current=True,status='draft',title=title,slug='nexa-eksport-markdown-basic',
        lead='Nexa Studio udostępnia eksport Markdown.', content=body,generated_content=body,meta_title=title,
        meta_description=ISSUES['seo_issue'][1] if 'seo_issue' in types else 'Potwierdzone informacje o eksporcie Markdown i cenie Nexa Basic.',
        article_type='news',brief=brief,sections=sections,lead_fact_ids=[ids[0]],generation_options={'length':'short'},
        research_snapshot=dict(candidate_id=candidate.id,research_id=research.id,facts=facts,sources=sources,uncertainties=research.uncertainties,conflicts=research.conflicts),
        word_count=len(body.split()),sections_count=2,facts_used_count=2,facts_available_count=len(facts),source_count=len(sources),
        parent_version_id=parent.id if parent else None,created_by='auto_fix' if parent else 'generated',creation_reason='QA auto fix (demo)' if parent else 'Seed demo',
        auto_fix_iteration=parent.auto_fix_iteration+1 if parent else 0,llm_model='demo-static',estimated_cost_usd=0,brief_llm_model='demo-static',brief_cost_usd=0,writer_cost_usd=0)
    a.content_hash=content_hash({field:getattr(a,field) for field in ('title','slug','lead','content','meta_title','meta_description')})
    session.add(a); await session.flush(); return a

async def _qa(session, article, types=(), status='completed', job=None):
    payload=build_qa_payload(article)
    issues=[]
    for typ in types:
        severity,excerpt,reason,suggestion,fixable=ISSUES[typ]
        fids=([article.research_snapshot['facts'][1 if typ=='incorrect_number' else 2]['id']] if typ in ('incorrect_number','incorrect_date','contradiction') else [])
        issues.append(dict(type=typ,severity=severity,excerpt=excerpt,reason=reason,suggestion=suggestion,section_heading='Funkcje i cena' if typ not in ('title_mismatch','seo_issue') else None,
            fact_ids=fids,source_ids=[article.research_snapshot['sources'][0]['id']] if fids else [],auto_fixable=fixable))
    qa=ArticleQA(article_id=article.id,article_version=article.version,status=status,job_id=job.id if job else None,input_snapshot=payload,input_hash=input_hash(payload),
        llm_model='demo-static',llm_input_tokens=0,llm_output_tokens=0,estimated_cost_usd=0,pass_score=85,issues=[])
    if status=='completed':
        output=QAOutput(factual_score=95,source_score=95,style_score=95,structure_score=95,seo_score=95,summary='Raport demonstracyjny: '+('wskazane problemy wymagają weryfikacji.' if types else 'materiał oparty na Research.'),issues=issues,
            claims=[dict(excerpt=article.lead,section_heading='Lead',verdict='supported',fact_ids=article.lead_fact_ids,source_ids=[article.research_snapshot['sources'][0]['id']])])
        output=validate_output(output,payload,validate_references(payload))
        for key,value in calculate_scores(output,85).items(): setattr(qa,key,value)
        qa.summary=output.summary; qa.claims=[c.model_dump(mode='json') for c in output.claims]
        qa.issues=[ArticleQAIssue(**i.model_dump(mode='json')) for i in output.issues]
        article.qa_passed=qa.qa_passed
        article.status='ready_for_approval' if qa.qa_passed else 'needs_changes'
    session.add(qa); await session.flush(); return qa

async def _job(session,candidate,kind,status,article=None,stage=None):
    now=datetime.now(timezone.utc); future=datetime(2100,1,1,tzinfo=timezone.utc)
    job=Job(id=uuid4(),candidate_id=candidate.id,workspace_id=candidate.workspace_id,article_id=article.id if article else None,kind=kind,status=status,
        payload={'demo':True,'demo_snapshot':True,'options':{'article_id':article.id} if article else {},'settings':{}},request_hash=input_hash([candidate.id,kind,status]),
        stage=stage or {'research':'extracting_sources','write':'writing_article','qa_article':'evaluating_qa','auto_fix_article':'fixing_article'}.get(kind),
        available_at=future,attempt_count=0 if status=='queued' else 1,max_attempts=3,
        worker_id='demo-snapshot' if status=='running' else None,lease_token=uuid4() if status=='running' else None,locked_until=future if status=='running' else None,
        started_at=now if status!='queued' else None,finished_at=now if status in ('failed','succeeded') else None,
        error_code='demo_failure' if status=='failed' else None,error_message='Przykładowy błąd. Retry demo nie używa AI.' if status=='failed' else None)
    session.add(job); await session.flush()
    if status!='queued': session.add(JobAttempt(job_id=job.id,number=1,worker_id='demo-snapshot',outcome='failed' if status=='failed' else 'retryable_error' if status=='retrying' else 'succeeded' if status=='succeeded' else 'running',last_stage=job.stage,
        finished_at=now if status!='running' else None,llm_calls=[]))
    return job

async def _fix(session,source,qa,result=None,status='completed',job=None,skipped=False,iteration=None):
    from difflib import SequenceMatcher
    snapshot={'article_id':source.id,'qa_id':qa.id,'issues':[{'id':i.id,'type':i.type,'excerpt':i.excerpt} for i in qa.issues]}
    fields=('title','lead','content','meta_title','meta_description')
    remaining=' '.join(getattr(result,f) for f in fields) if result else ''
    fixed=[i for i in qa.issues if result and i.auto_fixable and i.excerpt and i.excerpt not in remaining]
    fixed_ids={i.id for i in fixed}
    skipped_issues=[i for i in qa.issues if i.id not in fixed_ids] if result or skipped else []
    ratio=1-SequenceMatcher(None,source.content,result.content,autojunk=False).ratio() if result else 0
    changes=[dict(field='content',before=i.excerpt,after='',qa_issue_ids=[i.id],fact_ids=[],source_ids=[]) for i in fixed]
    fix=ArticleFix(source_article_version_id=source.id,result_article_version_id=result.id if result else None,qa_id=qa.id,status=status,
        job_id=job.id if job else None,iteration=iteration or source.auto_fix_iteration+1,input_hash=input_hash(snapshot),input_snapshot=snapshot,issues_requested=len(qa.issues),
        issues_fixed=len(fixed),issues_skipped=len(skipped_issues),
        summary=None if status in ('pending','running') else 'Błąd demo: nie utworzono nowej wersji.' if status=='failed' else 'Pominięto: brak bezpiecznej poprawki.' if skipped else 'Usunięto wskazane fragmenty; pozostałe issue wymagają kolejnej weryfikacji.' if skipped_issues else 'Usunięto niepoparte zdanie; zachowano pozostały tekst.',change_ratio=ratio,
        changes=changes,warnings=[],llm_model='demo-static',llm_input_tokens=0,llm_output_tokens=0,estimated_cost_usd=0,
        issues=[ArticleFixIssue(qa_issue_id=i.id,status='failed' if status=='failed' else 'fixed' if i.id in fixed_ids else 'skipped',
            reason='Usunięto fragment.' if i.id in fixed_ids else 'Wymagana dalsza lub ręczna weryfikacja.') for i in qa.issues] if status in ('completed','failed') else [])
    session.add(fix); await session.flush(); return fix

async def _populate(session,candidate,slug):
    if slug in ('discovered','classified','ignored'): return
    research=await _research(session,candidate)
    if slug.startswith('research-') and slug!='research-ready':
        status=slug.removeprefix('research-');job=await _job(session,candidate,'research',status)
        research.job_id=job.id; research.status='pending' if status=='queued' else status
        if status=='failed': research.error=job.error_message
        research.facts.clear(); return
    if slug=='queue-retrying':
        j=await _job(session,candidate,'research','retrying');j.error_code='demo_transient_error';j.error_message='Przykładowy błąd przejściowy; zaplanowano automatyczny retry.';research.job_id=j.id;research.status='pending';research.facts.clear();return
    if slug=='research-ready': return
    if slug in ('write-queued','brief-running','write-failed'):
        await _job(session,candidate,'write','running' if slug=='brief-running' else slug.removeprefix('write-'),stage='building_brief' if slug=='brief-running' else None);return
    typemap={'qa-unsupported':['unsupported_claim'],'qa-quote':['unsupported_quote'],'qa-date':['contradiction'], 'qa-number':['incorrect_number'], 'qa-uncertainty':['missing_uncertainty'], 'qa-conflict':['ignored_conflict'],
        'qa-editorial':['title_mismatch','repetition','style_issue','structure_issue','seo_issue'], 'qa-references':['source_mismatch'], 'qa-catalog':list(ISSUES),'qa-warnings':['repetition','style_issue']}
    types=typemap.get(slug, ['unsupported_claim'] if slug.startswith('fix-') else [])
    if slug=='fix-needs-changes': types=['unsupported_claim','overclaim']
    if slug=='fix-limit': types=['unsupported_claim','overclaim','unsupported_quote']
    a=await _article(session,candidate,research,types=types)
    if slug=='draft': return
    if slug in ('qa-queued','qa-running','qa-failed'):
        status=slug.removeprefix('qa-');j=await _job(session,candidate,'qa_article',status,a);await _qa(session,a,status='pending' if status=='queued' else status,job=j);return
    q=await _qa(session,a,types)
    if slug.startswith('fix-'):
        if slug in ('fix-queued','fix-running','fix-failed'):
            status=slug.removeprefix('fix-');j=await _job(session,candidate,'auto_fix_article',status,a);await _fix(session,a,q,status='pending' if status=='queued' else status,job=j);return
        if slug=='fix-skipped':
            await _fix(session,a,q,skipped=True); a.status='manual_review_required';return
        still_bad=slug in ('fix-needs-changes','fix-limit')
        remaining_types=['overclaim','unsupported_quote'] if slug=='fix-limit' else ['overclaim'] if still_bad else []
        child=await _article(session,candidate,research,version=2,parent=a,types=remaining_types)
        await _fix(session,a,q,child)
        if slug=='fix-qa':
            j=await _job(session,candidate,'qa_article','queued',child); await _qa(session,child,status='pending',job=j);return
        childqa=await _qa(session,child,remaining_types)
        if slug=='fix-limit':
            third=await _article(session,candidate,research,version=3,parent=child,types=['unsupported_quote'])
            await _fix(session,child,childqa,third,iteration=2);await _qa(session,third,['unsupported_quote']);third.status='manual_review_required'
        return
    if slug in ('approved','superseded','manual-edit'):
        a.status='approved';a.approved_at=datetime.now(timezone.utc)
        if slug=='superseded':
            a.status='superseded';child=await _article(session,candidate,research,version=2,parent=a);child.created_by='regenerated';child.auto_fix_iteration=0
            await _qa(session,child);child.status='approved';child.approved_at=datetime.now(timezone.utc)
        if slug=='manual-edit':
            child=await _article(session,candidate,research,version=2,parent=a);child.created_by='manual_edit';child.creation_reason='Ręczna edycja (demo)';child.auto_fix_iteration=0;child.is_edited=True
    if slug=='rejected': a.status='rejected';a.rejection_reason='Potrzebna zmiana kąta artykułu — przykład demo.'
    if slug=='qa-stale':
        a.meta_description+=' Zmieniony opis po starym QA.';a.qa_passed=False;a.status='draft'
        a.content_hash=content_hash({field:getattr(a,field) for field in ('title','slug','lead','content','meta_title','meta_description')})

async def seed_demo(session, workspace_id=None):
    """Insert missing cases atomically. Existing demo edits and real content survive."""
    await session.execute(text('SELECT pg_advisory_xact_lock(7642107)'))
    workspace_id=await resolve_workspace(session,workspace_id)
    source=await session.scalar(select(Source).where(Source.url==DEMO_PREFIX+'feed.xml',Source.workspace_id==workspace_id))
    if source is None:
        source=Source(workspace_id=workspace_id,name='[DEMO] Scenariusze pipeline — 0 kosztów AI',url=DEMO_PREFIX+'feed.xml',active=False)
        session.add(source);await session.flush()
    catalog=[]
    for index,(slug,title,description) in enumerate(CASES,1):
        url=DEMO_PREFIX+'cases/'+slug
        candidate=await session.scalar(select(Candidate).where(Candidate.external_url==url,Candidate.workspace_id==workspace_id))
        if candidate is None:
            candidate=Candidate(workspace_id=workspace_id,source_id=source.id,external_url=url,title=f'[DEMO {index:02}] {title}',summary=description,
                original_published_at=datetime.now(timezone.utc),status='ignored' if slug=='ignored' else 'pending',
                category=None if slug=='discovered' else 'news',total_score=None if slug=='discovered' else 90,
                relevance_score=None if slug=='discovered' else 90,freshness_score=None if slug=='discovered' else 90,search_potential_score=None if slug=='discovered' else 90,commercial_potential_score=None if slug=='discovered' else 90,
                llm_reason=None if slug=='discovered' else 'Syntetyczna ocena demo — nie wywołano AI.',llm_model='demo-static',llm_input_tokens=0,llm_output_tokens=0,estimated_cost_usd=0,
                classified_at=None if slug=='discovered' else datetime.now(timezone.utc))
            session.add(candidate);await session.flush();await _populate(session,candidate,slug)
        # Repair only the exact initial demo fixture shape, never user-supplied material.
        existing_research=await session.scalar(select(Research).where(Research.candidate_id==candidate.id))
        if existing_research and existing_research.uncertainties==[{'description':'Cena Enterprise nie została potwierdzona.', 'source_ids':[existing_research.sources[0].id]}]:
            existing_research.uncertainties=[{'claim':'Cena Enterprise','reason':'Cena Enterprise nie została potwierdzona.'}]
            existing_research.conflicts=[{'topic':'Region hostingu','sources':[{'url':s.url,'claim':region} for s,region in zip(existing_research.sources,('Europa','USA'))]}]
        catalog.append(dict(slug=slug,title=title,description=description,candidate_id=candidate.id,url=f'/candidates/{candidate.id}'))
    await session.commit();return catalog

async def main():
    parser=argparse.ArgumentParser(description='Scenariusze demo bez wywołań AI');workspace_argument(parser)
    async with SessionLocal() as session:
        try: catalog=await seed_demo(session,parser.parse_args().workspace)
        except WorkspaceNotFound as exc: sys.exit(str(exc))
    print('DEMO: bez wywołań AI. Istniejące dane zachowane. Instrukcja: docs/demo/README.md')
    for c in catalog: print(f"{c['candidate_id']:>5}  {c['slug']:<22} http://localhost:3000{c['url']}")

if __name__=='__main__': asyncio.run(main())
