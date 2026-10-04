"""Reference validation and deterministic scores; no external I/O."""
import logging
import re
from decimal import Decimal, ROUND_HALF_UP

from app.schemas.qa import QAOutput, QAIssueOutput
from app.services.llm.base import LLMError

logger = logging.getLogger(__name__)
FACTUAL_TYPES = {'unsupported_claim', 'contradiction', 'incorrect_number', 'incorrect_date',
                 'unsupported_quote', 'unsupported_name', 'missing_uncertainty', 'ignored_conflict', 'overclaim'}
SCORE_WEIGHTS = {'factual_score': 40, 'source_score': 20, 'style_score': 15,
                 'structure_score': 15, 'seo_score': 10}


def normalize(text):
    return re.sub(r'\s+', ' ', text).strip().casefold()


def key(excerpt, heading):
    return normalize(excerpt), normalize(heading or '')


def same_claim(a, b):
    left, right = key(a.excerpt, a.section_heading), key(b.excerpt, b.section_heading)
    return left[1] == right[1] and bool(left[0] and right[0]) and (left[0] in right[0] or right[0] in left[0])


def reference_sets(payload):
    research = payload['research']
    return {f['id'] for f in research['facts']}, {s['id'] for s in research['sources']}


def keep_ids(ids, allowed, kind):
    result = []
    for value in dict.fromkeys(ids):
        if value in allowed:
            result.append(value)
        else:
            logger.warning('QA invalid %s reference id=%s', kind, value)
    return result


def validate_references(payload):
    facts, sources = reference_sets(payload)
    article = payload['article']
    records = [dict(heading='Lead', used_fact_ids=article['lead_fact_ids'], source_ids=[])]
    records += article['sections']
    brief = payload.get('brief', {})
    records += [dict(heading='Brief', used_fact_ids=brief.get('required_facts', []) +
                    brief.get('optional_facts', []), source_ids=[])]
    records += [dict(heading=f"Brief: {s.get('heading', '')}",
                    used_fact_ids=s.get('fact_ids', []), source_ids=[])
                for s in brief.get('section_plan', [])]
    issues = []
    by_id = {f['id']: f for f in payload['research']['facts']}
    for section in records:
        for field, allowed in [('used_fact_ids', facts), ('source_ids', sources)]:
            invalid = [i for i in dict.fromkeys(section.get(field, [])) if i not in allowed]
            if invalid:
                logger.warning('QA invalid article references field=%s ids=%s', field, invalid)
                issues.append(QAIssueOutput(type='source_mismatch', severity='warning', excerpt='',
                    reason=f"Nieprawidłowe referencje {field}: {invalid}. Nie należą do snapshotu researchu tej wersji.",
                    suggestion='Zweryfikuj przypisanie faktów i źródeł.', section_heading=section.get('heading'),
                    fact_ids=[], source_ids=[], auto_fixable=False))
        section_sources = set(section.get('source_ids', [])) & sources
        mismatched = [fid for fid in section.get('used_fact_ids', []) if fid in by_id and
                      section_sources and not section_sources.intersection(by_id[fid].get('source_ids', []))]
        if mismatched:
            issues.append(QAIssueOutput(type='source_mismatch', severity='warning', excerpt='',
                reason=f"Przypisane źródła nie wspierają wskazanych faktów: {mismatched}.",
                suggestion='Sprawdź powiązania faktów ze źródłami.', section_heading=section.get('heading'),
                fact_ids=mismatched, source_ids=sorted(section_sources), auto_fixable=False))
    # Snapshot evidence must itself have valid fact -> source relations.
    for fact in payload['research']['facts']:
        invalid = [i for i in fact.get('source_ids', []) if i not in sources]
        if invalid:
            logger.warning('QA fact=%s missing snapshot sources=%s', fact['id'], invalid)
            issues.append(QAIssueOutput(type='source_mismatch', severity='warning', excerpt='',
                reason=f"Fakt {fact['id']} odwołuje się do źródeł niedostępnych w snapshotcie: {invalid}.",
                suggestion='Sprawdź kompletność materiałów tej wersji.', section_heading=None,
                fact_ids=[fact['id']], source_ids=[], auto_fixable=False))
    return issues



def literal_seo_excerpt(item, article):
    """Repair field labels only when every supplied value exactly matches a current field."""
    if item.type != 'seo_issue':return item
    pattern=r'(?m)^(title|meta_title|meta_description|lead|slug):[ \t]*'
    matches=list(re.finditer(pattern,item.excerpt))
    if not matches or item.excerpt[:matches[0].start()].strip():return item
    fields=[]
    for index,match in enumerate(matches):
        field=match.group(1)
        end=matches[index+1].start() if index+1<len(matches) else len(item.excerpt)
        value=item.excerpt[match.end():end].strip()
        if not value or normalize(value)!=normalize(article.get(field,'')) or field in fields:return item
        fields.append(field)
    # Keep one real field as the edit anchor; reason/suggestion retain the cross-field observation.
    field=next((f for f in fields if f.startswith('meta_')),fields[0])
    heading='SEO' if field.startswith('meta_') or field=='slug' else 'Lead' if field=='lead' else 'Title'
    return item.model_copy(update={'excerpt':article[field],'section_heading':heading})


def validate_output(output, payload, reference_issues):
    output = QAOutput.model_validate(output)
    facts, sources = reference_sets(payload)
    article_text = ' '.join(str(payload['article'].get(name, ''))
                            for name in ('title', 'lead', 'content', 'meta_title', 'meta_description', 'slug'))
    normalized_text = normalize(article_text)
    output=output.model_copy(update={'issues':[literal_seo_excerpt(item,payload['article']) for item in output.issues]})
    for item in output.issues:
        if item.excerpt and normalize(item.excerpt) not in normalized_text:
            raise LLMError('Odpowiedź QA zawiera fragment spoza aktualnego artykułu.', code='invalid_output')
    relation_issues = []
    fact_sources = {f['id']: set(f.get('source_ids', [])) for f in payload['research']['facts']}

    def clean_references(item):
        fids = keep_ids(item.fact_ids, facts, 'fact')
        sids = keep_ids(item.source_ids, sources, 'source')
        if fids and sids:
            supporting = set().union(*(fact_sources[fid] for fid in fids))
            # A source may independently support another clause (e.g. both sides of a conflict).
            # Reject a disjoint fact/source pairing, not additional evidence alongside a valid pairing.
            mismatched = sids if not set(sids).intersection(supporting) else []
            if mismatched:
                logger.warning('QA mismatched fact/source relation facts=%s sources=%s', fids, mismatched)
                sids = [sid for sid in sids if sid in supporting]
                relation_issues.append(QAIssueOutput(type='source_mismatch', severity='warning', excerpt=item.excerpt,
                    reason=f"Źródła {mismatched} nie wspierają wskazanych faktów {fids}.",
                    suggestion='Użyj źródeł przypisanych do tych faktów.', section_heading=item.section_heading,
                    fact_ids=fids, source_ids=sids, auto_fixable=False))
        return fids, sids

    claims = []
    for claim in output.claims:
        if normalize(claim.excerpt) not in normalized_text:
            if claim.verdict != 'supported':
                raise LLMError('Odpowiedź QA zawiera niepoparty fragment spoza artykułu.', code='invalid_output')
            logger.warning('QA omitted supported claim without literal article excerpt')
            continue
        fids, sids = clean_references(claim)
        verdict = claim.verdict
        if verdict == 'supported' and not (fids or sids):
            verdict = 'unsupported'
        claims.append(claim.model_copy(update=dict(fact_ids=fids, source_ids=sids, verdict=verdict)))
    if not claims:
        raise LLMError('QA nie wskazuje żadnego ocenionego fragmentu artykułu.', code='invalid_output')
    issues = []
    for item in output.issues:
        if item.type == 'ignored_conflict' and item.severity == 'info' and any(
                c.verdict == 'supported' and same_claim(c, item) for c in claims) and not any(
                c.verdict != 'supported' and same_claim(c, item) for c in claims):
            logger.warning('QA omitted informational conflict observation already assessed as supported')
            continue
        if item.type in FACTUAL_TYPES and not item.excerpt.strip():
            raise LLMError('Problem faktyczny QA nie wskazuje fragmentu artykułu.', code='invalid_output')
        fids, sids = clean_references(item)
        issues.append(item.model_copy(update=dict(fact_ids=fids, source_ids=sids)))
    for claim in claims:
        if claim.verdict != 'supported' and not any(same_claim(i, claim) and i.type in FACTUAL_TYPES for i in issues):
            issues.append(QAIssueOutput(type='unsupported_claim', severity='high', excerpt=claim.excerpt,
                reason='Twierdzenie nie ma potwierdzenia w dostarczonym researchu.',
                suggestion='Usuń twierdzenie lub oprzyj je na dostępnym materiale.',
                section_heading=claim.section_heading, fact_ids=claim.fact_ids,
                source_ids=claim.source_ids, auto_fixable=True))
    seen = set()
    combined = []
    for item in issues + reference_issues + relation_issues:
        identity = (item.type, key(item.excerpt, item.section_heading), item.reason)
        if identity not in seen:
            seen.add(identity)
            combined.append(item)
    return output.model_copy(update=dict(claims=claims, issues=combined))


def calculate_scores(output, threshold):
    partials = {name: getattr(output, name) for name in SCORE_WEIGHTS}
    overall = int((sum(Decimal(partials[n]) * w for n, w in SCORE_WEIGHTS.items()) /
                   100).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
    critical = sum(i.severity == 'critical' for i in output.issues)
    if critical:
        overall = min(overall, 60)
    if any(i.type == 'unsupported_claim' and i.severity == 'high' for i in output.issues):
        overall = min(overall, 75)
    unsupported_claims = [c for c in output.claims if c.verdict != 'supported' or
                          any(i.type in FACTUAL_TYPES and same_claim(c, i) for i in output.issues)]
    unsupported = {key(c.excerpt, c.section_heading) for c in unsupported_claims}
    unsupported |= {key(i.excerpt, i.section_heading) for i in output.issues
                    if i.type in FACTUAL_TYPES and i.excerpt and
                    not any(same_claim(c, i) for c in unsupported_claims)}
    supported = {key(c.excerpt, c.section_heading) for c in output.claims
                 if c.verdict == 'supported' and not any(i.type in FACTUAL_TYPES and same_claim(c, i)
                     for i in output.issues)} - unsupported
    return dict(**partials, overall_score=overall, supported_claims_count=len(supported),
                unsupported_claims_count=len(unsupported), critical_issue_count=critical,
                warning_count=sum(i.severity == 'warning' for i in output.issues),
                qa_passed=overall >= threshold and critical == 0 and not unsupported)
