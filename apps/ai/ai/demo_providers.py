# Rola pliku: Deterministyczni dostawcy trybu demo: stałe odpowiedzi bez sieci i bez kosztu.

"""Deterministic synthetic providers; no HTTP client, DNS, SDK or paid calls."""
import re
from dataclasses import asdict
from datetime import UTC, datetime

from app.demo import DEMO_MODEL, DEMO_PREFIX
from app.schemas.article import ArticleBrief, WriterOutput, WriterSection
from app.schemas.classification import CandidateClassification
from app.schemas.research import ResearchOutput, SearchQueries
from app.schemas.qa import QAOutput
from app.schemas.auto_fix import FixOutput
from app.services.llm.base import LLMUsage, QueriesResult, ResearchResult, BriefResult, WriterResult
from app.services.llm.qa import QAResult
from app.services.llm.auto_fix import FixResult
from app.services.research.content_extractor import ExtractedDocument
from app.services.research.search import SearchResult

PRICE = 'Nexa Basic kosztuje 9,99 USD miesięcznie.'
EXPORT = 'Nexa Studio udostępnia eksport Markdown.'
LAUNCH = 'Nexa Studio uruchomiono 1 czerwca 2026 roku.'
UNSUPPORTED = 'Nexa zwiększa produktywność o 47%.'
USAGE = LLMUsage(DEMO_MODEL, 0, 0)


class DemoExtractor:
    async def extract(self, url):
        # Even manually added public URLs remain local in a demo research.
        return ExtractedDocument(url=url, title='Nexa Studio — materiały demonstracyjne', author=None,
            published_at=datetime(2026, 6, 1, tzinfo=UTC), publisher='Nexa Research (demo)',
            content='\n\n'.join([PRICE, EXPORT, LAUNCH,
                'Termin udostępnienia Nexa Enterprise nie został potwierdzony.',
                'Materiały podają różne regiony hostingu: Europa i USA.']),
            http_status=200, method='demo-static')


class DemoSearch:
    async def search(self, query, limit=5):
        return [SearchResult(url=DEMO_PREFIX + 'sources/nexa-pricing', title='Nexa — cennik (demo)',
            snippet=PRICE), SearchResult(url=DEMO_PREFIX + 'sources/nexa-docs',
            title='Nexa — dokumentacja (demo)', snippet=EXPORT)][:limit]


class DemoClassifier:
    async def classify_candidate(self, candidate, editorial=None):
        result = CandidateClassification(relevance=90, freshness=80, search_potential=85,
            commercial_potential=70, category='news', reason='Symulowana klasyfikacja tematu Nexa Studio.')
        result._usage = asdict(USAGE)
        return result


class DemoResearcher:
    async def generate_search_queries(self, candidate):
        return QueriesResult(SearchQueries(queries=['Nexa Studio demo cennik', 'Nexa Studio demo dokumentacja']), USAGE)

    async def research(self, candidate, documents):
        urls = [d.url for d in documents]
        output = ResearchOutput(summary='Nexa Studio: syntetyczna premiera i cennik.',
            why_it_matters='Przykład weryfikacji faktów i korekty artykułu.',
            suggested_angle='Cena, eksport i zakres potwierdzonych informacji.',
            facts=[dict(claim=claim, importance='critical' if index == 0 else 'important',
                basis='verifiable', confidence=100, source_urls=urls)
                for index, claim in enumerate([PRICE, EXPORT, LAUNCH])],
            uncertainties=[dict(claim='Termin udostępnienia Nexa Enterprise', reason='Brak potwierdzenia w materiałach.')],
            conflicts=[dict(topic='Region hostingu', sources=[dict(url=urls[0], claim='Europa'),
                dict(url=urls[-1], claim='USA')])],
            source_types=[dict(url=url, source_type='official') for url in urls])
        return ResearchResult(output, USAGE)


class DemoWriter:
    async def generate_brief(self, context):
        return BriefResult(ArticleBrief(article_type=context.article_type,
            article_format=context.article_format if context.article_format in {'news','explainer','case_study','guide','comparison'} else 'news', primary_angle='Potwierdzone informacje o Nexa Studio',
            target_audience='Redaktorzy testujący przepływ aplikacji', suggested_title='Nexa Studio: cena i eksport Markdown',
            key_points=[f.claim for f in context.facts], required_facts=[f.id for f in context.facts],
            optional_facts=[], uncertainties_to_avoid=['Termin Nexa Enterprise'], conflicts_to_mention=[],
            desired_length_words=400), USAGE)

    async def write_article(self, context, brief):
        facts = context.facts
        return WriterResult(WriterOutput(title=brief.suggested_title, slug='nexa-studio-demo',
            lead=facts[0].claim, lead_fact_ids=[facts[0].id],
            sections=[WriterSection(heading='Co potwierdzają materiały',
                content='\n\n'.join(f.claim for f in facts) + '\n\n' + UNSUPPORTED,
                used_fact_ids=[f.id for f in facts], source_ids=sorted({s for f in facts for s in f.source_ids}))],
            conclusion='Zakres funkcji warto porównać z potrzebami redakcji.', conclusion_fact_ids=[],
            meta_title=brief.suggested_title, meta_description=EXPORT), USAGE)


def article_fragments(article):
    for field in ('title', 'lead', 'content', 'meta_title', 'meta_description'):
        for paragraph in re.split(r'\n\s*\n', article.get(field) or ''):
            if paragraph.strip() and not paragraph.lstrip().startswith('#'):
                yield field, paragraph.strip()


class DemoQA:
    async def evaluate(self, payload):
        article, facts = payload['article'], payload['research']['facts']
        issues, claims, seen = [], [], set()
        for field, fragment in article_fragments(article):
            heading = {'title':'Title', 'lead':'Lead', 'meta_title':'SEO', 'meta_description':'SEO'}.get(field)
            for fact in facts:
                if fact['claim'] in fragment and (fact['claim'], heading) not in seen:
                    seen.add((fact['claim'], heading))
                    claims.append(dict(excerpt=fact['claim'], section_heading=heading, verdict='supported',
                        fact_ids=[fact['id']], source_ids=fact.get('source_ids', [])))
            issue_type = None
            excerpt = fragment
            if '47%' in fragment:
                issue_type, severity = 'unsupported_claim', 'high'
                if UNSUPPORTED in fragment: excerpt = UNSUPPORTED
            elif any(mark in fragment for mark in ('„', '"', '“')) and not any(fragment in f['claim'] for f in facts):
                issue_type, severity = 'unsupported_quote', 'critical'
            elif ('Enterprise' in fragment and not any(word in fragment.casefold() for word in ('niepotwierdz', 'nie został', 'niepewn', 'brak', 'nie podano'))):
                issue_type, severity = 'missing_uncertainty', 'high'
            elif 'wyłącznie w Europie' in fragment:
                issue_type, severity = 'ignored_conflict', 'high'
            elif '19,99' in fragment or '29,99' in fragment or re.search(r'(?<![\d,])99 USD', fragment):
                issue_type, severity = 'incorrect_number', 'high'
            elif '2025' in fragment:
                issue_type, severity = 'contradiction', 'critical'
            elif '2027' in fragment or '2 czerwca 2026' in fragment:
                issue_type, severity = 'incorrect_date', 'high'
            elif 'Eksport Markdown jest dostępny. Eksport Markdown jest dostępny.' in fragment:
                issue_type, severity = 'repetition', 'warning'
            elif 'Warto zauważyć. Nie ulega wątpliwości.' in fragment:
                issue_type, severity = 'style_issue', 'warning'
            elif 'Ta sekcja powtarza lead i nie rozwija tematu.' in fragment:
                issue_type, severity = 'structure_issue', 'warning'
            elif 'Nexa gwarantuje podwojenie wyników' in fragment:
                issue_type, severity = 'title_mismatch', 'warning'
            elif 'Najlepszy produkt z gwarancją wyników' in fragment:
                issue_type, severity = 'seo_issue', 'warning'
            elif 'Nexa jest bezkonkurencyjna na całym rynku.' in fragment:
                issue_type, severity = 'overclaim', 'high'
            elif 'Twórcą Nexa jest Jan Kowalski.' in fragment:
                issue_type, severity = 'unsupported_name', 'high'
            if issue_type and (excerpt, heading) not in seen:
                seen.add((excerpt, heading))
                evidence = next((f for f in facts if (issue_type == 'incorrect_number' and 'kosztuje' in f['claim']) or
                    (issue_type == 'incorrect_date' and '2026' in f['claim'])), None)
                fids = [evidence['id']] if evidence else []
                sids = evidence.get('source_ids', []) if evidence else []
                issues.append(dict(type=issue_type, severity=severity, excerpt=excerpt,
                    reason='Fragment nie jest zgodny z syntetycznymi materiałami Nexa Research.',
                    suggestion='Popraw zgodnie z potwierdzonym faktem.' if evidence else 'Usuń niepotwierdzone twierdzenie.',
                    section_heading=heading, fact_ids=fids, source_ids=sids,
                    auto_fixable=issue_type in {'unsupported_claim', 'incorrect_number', 'incorrect_date', 'repetition', 'style_issue', 'structure_issue', 'title_mismatch', 'seo_issue', 'overclaim'}))
                if severity != 'warning':
                    claims.append(dict(excerpt=excerpt, section_heading=heading, verdict='contradicted' if evidence else 'unsupported',
                        fact_ids=fids, source_ids=sids))
        if not claims:
            # Honest fallback for an edited text without one of the fixture facts.
            field, fragment = next(article_fragments(article))
            claims.append(dict(excerpt=fragment, section_heading=None, verdict='unsupported', fact_ids=[], source_ids=[]))
            issues.append(dict(type='unsupported_claim', severity='high', excerpt=fragment,
                reason='Brak potwierdzonego faktu w materiałach demonstracyjnych.', suggestion='Oprzyj treść na Nexa Research.',
                section_heading=None, fact_ids=[], source_ids=[], auto_fixable=True))
        factual_issues = {'unsupported_claim', 'unsupported_quote', 'unsupported_name', 'contradiction', 'incorrect_number', 'incorrect_date', 'missing_uncertainty', 'ignored_conflict', 'overclaim'}
        output = QAOutput(factual_score=65 if any(i['type'] in factual_issues for i in issues) else 100, source_score=100, style_score=95,
            structure_score=95, seo_score=95, summary='Symulowane QA: wykryto problemy.' if issues else 'Potwierdzone fakty Nexa Research.',
            issues=issues, claims=claims)
        return QAResult(output, USAGE)


class DemoFix:
    async def fix(self, payload):
        patches, results = [], []
        facts = {f['id']: f for f in payload['research']['facts']}
        used = set()
        for issue in payload['issues']:
            found = next((field for field in ('content', 'lead', 'title', 'meta_title', 'meta_description')
                if payload['article'].get(field, '').count(issue['excerpt']) == 1 and (field, issue['excerpt']) not in used), None)
            if issue['auto_fixable'] and found:
                fact = next((facts[i] for i in issue['fact_ids'] if i in facts), None)
                after = fact['claim'] if fact and issue['type'] in ('incorrect_number', 'incorrect_date') else ''
                if found != 'content' and not after:
                    fact = next(iter(facts.values()), None)
                    if fact is None:
                        results.append(dict(qa_issue_id=issue['id'], status='skipped', reason='Brak faktu dla wymaganego pola.'))
                        continue
                    after = fact['claim']
                patches.append(dict(field=found, before=issue['excerpt'], after=after,
                    qa_issue_ids=[issue['id']], fact_ids=[fact['id']] if fact else [],
                    source_ids=fact.get('source_ids', []) if fact else []))
                used.add((found, issue['excerpt']))
                results.append(dict(qa_issue_id=issue['id'], status='fixed', reason='Usunięto problem wskazany przez QA.'))
            else:
                results.append(dict(qa_issue_id=issue['id'], status='skipped', reason='Wymagana ręczna weryfikacja fragmentu.'))
        return FixResult(FixOutput(summary='Symulowana korekta na podstawie aktualnego QA.', patches=patches, fix_results=results), USAGE)


class DemoEmbedder:
    """Deterministyczne wektory bez API: wspólne słowa dają podobne wektory, więc demo grupuje podobne tytuły."""
    async def embed(self, texts):
        import hashlib, math, re
        from app.services.llm.embeddings import DIMENSIONS, EmbedResult
        vectors = []
        for text in texts:
            vector = [0.0] * DIMENSIONS
            for word in re.findall(r'\w{3,}', text.lower()):
                vector[int(hashlib.sha256(word.encode()).hexdigest(), 16) % DIMENSIONS] += 1.0
            norm = math.sqrt(sum(v * v for v in vector)) or 1.0
            vectors.append([v / norm for v in vector])
        return EmbedResult(vectors, USAGE)


def demo_providers():
    return {'classify': DemoClassifier(), 'embed': DemoEmbedder(), 'research': DemoResearcher(), 'write': DemoWriter(),
        'qa_article': DemoQA(), 'auto_fix_article': DemoFix(), 'extractor': DemoExtractor(), 'search': DemoSearch()}
