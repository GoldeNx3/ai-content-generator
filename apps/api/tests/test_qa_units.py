import pytest
from pydantic import ValidationError

from app.schemas.qa import QAOutput
from app.services.qa.validation import calculate_scores, validate_output, validate_references


def output(**changes):
    data = dict(factual_score=96, source_score=90, style_score=88, structure_score=92,
                seo_score=85, summary='Ocena.', issues=[], claims=[dict(
                    excerpt='Barclays wdraża Claude.', section_heading=None, verdict='supported',
                    fact_ids=[1], source_ids=[2])])
    data.update(changes)
    return QAOutput.model_validate(data)


def issue(kind='unsupported_claim', severity='high', excerpt='47%'):
    return dict(type=kind, severity=severity, excerpt=excerpt, reason='Brak dowodu.',
                suggestion='Usuń twierdzenie.', section_heading=None, fact_ids=[],
                source_ids=[], auto_fixable=True)


def payload():
    return dict(article=dict(title='Barclays wdraża Claude.', lead='Barclays wdraża Claude.',
        content='Produktywność wzrosła o 47%.', meta_title='', meta_description='', slug='barclays',
        lead_fact_ids=[1], sections=[]), brief={}, research=dict(
        facts=[dict(id=1, claim='Barclays wdraża Claude.', source_ids=[2])], sources=[dict(id=2)]))


def test_clean_score_and_counts():
    result = calculate_scores(output(), 85)
    assert result['overall_score'] == 92
    assert result['supported_claims_count'] == 1
    assert result['unsupported_claims_count'] == 0
    assert result['qa_passed'] is True


@pytest.mark.parametrize('kind,severity,cap', [
    ('unsupported_claim', 'high', 75), ('unsupported_quote', 'critical', 60),
    ('contradiction', 'critical', 60), ('missing_uncertainty', 'warning', 100),
    ('ignored_conflict', 'high', 100), ('incorrect_number', 'high', 100),
])
def test_factual_issues_block_readiness(kind, severity, cap):
    checked = output(issues=[issue(kind, severity)])
    result = calculate_scores(checked, 85)
    assert result['overall_score'] <= cap
    assert result['unsupported_claims_count'] == 1
    assert not result['qa_passed']


@pytest.mark.parametrize('field,value', [('factual_score', 101), ('seo_score', -1),
    ('factual_score', 85.5), ('issues', [issue('made_up_type')]), ('claims', [])])
def test_malformed_output(field, value):
    with pytest.raises(ValidationError):
        output(**{field: value})


def test_invalid_fact_and_source_references(caplog):
    data = payload()
    data['article']['sections'] = [dict(heading='Sekcja', used_fact_ids=[999], source_ids=[998])]
    issues = validate_references(data)
    assert len(issues) == 2
    checked = output(issues=[{**issue(excerpt='47%'), 'fact_ids': [999], 'source_ids': [998]}])
    cleaned = validate_output(checked, data, issues)
    assert cleaned.issues[0].fact_ids == [] and cleaned.issues[0].source_ids == []
    assert '999' in caplog.text and '998' in caplog.text


def test_supported_claim_requires_known_evidence():
    checked = output(claims=[dict(excerpt='47%', section_heading=None,
        verdict='supported', fact_ids=[999], source_ids=[998])])
    cleaned = validate_output(checked, payload(), [])
    assert cleaned.claims[0].verdict == 'unsupported'
    assert calculate_scores(cleaned, 85)['unsupported_claims_count'] == 1


def test_duplicate_factual_findings_count_one_claim():
    checked = output(issues=[issue(), issue('incorrect_number')])
    assert calculate_scores(checked, 85)['unsupported_claims_count'] == 1


def test_hallucinated_excerpt_rejects_report():
    from app.services.llm.base import LLMError
    with pytest.raises(LLMError, match='fragment'):
        validate_output(output(claims=[dict(excerpt='Zmyślone zdanie.', section_heading=None,
            verdict='supported', fact_ids=[1], source_ids=[2])]), payload(), [])


def test_source_must_support_referenced_fact():
    data = payload()
    data['research']['sources'].append(dict(id=3))
    data['article']['sections'] = [dict(heading='Sekcja', used_fact_ids=[1], source_ids=[3])]
    assert any('nie wspierają' in i.reason for i in validate_references(data))


def test_empty_factual_issue_cannot_pass():
    from app.services.llm.base import LLMError
    with pytest.raises(LLMError):
        validate_output(output(issues=[issue('contradiction', 'high', '')]), payload(), [])


def test_snapshot_research_provenance():
    from types import SimpleNamespace
    from app.services.qa.context import build_qa_payload
    from app.services.jobs.errors import JobInputError
    article = SimpleNamespace(research_snapshot={'candidate_id': 1, 'research_id': 999,
        'facts': [{}], 'sources': [{}]}, candidate_id=1, research_id=2)
    with pytest.raises(JobInputError):
        build_qa_payload(article)


def test_output_source_relation_is_validated(caplog):
    data = payload()
    data['research']['sources'].append({'id': 3})
    checked = output(claims=[dict(excerpt='Barclays wdraża Claude.', section_heading=None,
        verdict='supported', fact_ids=[1], source_ids=[3])])
    cleaned = validate_output(checked, data, [])
    assert cleaned.claims[0].source_ids == []
    assert any(i.type == 'source_mismatch' for i in cleaned.issues)


def test_claim_and_shorter_issue_excerpt_count_once():
    checked = output(claims=[dict(excerpt='Produktywność wzrosła o 47%.', section_heading='Wpływ',
        verdict='unsupported', fact_ids=[], source_ids=[])], issues=[{**issue(), 'section_heading':'Wpływ'}])
    cleaned = validate_output(checked, payload(), [])
    assert len(cleaned.issues) == 1
    assert calculate_scores(cleaned, 85)['unsupported_claims_count'] == 1


def test_paraphrased_supported_claim_is_not_counted_as_quote():
    checked = output(claims=[*output().claims, dict(excerpt='Innymi słowami: bank adoptuje AI.',
        section_heading=None, verdict='supported', fact_ids=[1], source_ids=[2])])
    cleaned = validate_output(checked, payload(), [])
    assert len(cleaned.claims) == 1
    assert calculate_scores(cleaned, 85)['supported_claims_count'] == 1


def test_sources_can_supply_additional_evidence_beyond_named_fact():
    data = payload()
    data['research']['sources'].append({'id': 3})
    checked = output(claims=[dict(excerpt='Barclays wdraża Claude.', section_heading=None,
        verdict='supported', fact_ids=[1], source_ids=[2,3])])
    cleaned = validate_output(checked, data, [])
    assert cleaned.claims[0].source_ids == [2,3]
    assert not cleaned.issues


def test_informational_confirmation_of_described_conflict_is_not_a_defect():
    checked = output(issues=[issue('ignored_conflict', 'info', 'Barclays wdraża Claude.')])
    cleaned = validate_output(checked, payload(), [])
    assert not cleaned.issues
    assert calculate_scores(cleaned, 85)['qa_passed']


def test_half_score_rounds_up_and_threshold_is_configurable():
    checked = output(factual_score=85, source_score=85, style_score=87, structure_score=85, seo_score=87)
    assert calculate_scores(checked, 86)['overall_score'] == 86
    assert calculate_scores(checked, 86)['qa_passed']
    assert not calculate_scores(checked, 87)['qa_passed']


def test_unsupported_info_is_still_a_factual_problem():
    checked = output(issues=[issue('unsupported_claim', 'info')])
    assert not calculate_scores(checked, 85)['qa_passed']


def test_seo_labeled_existing_fields_become_single_literal_excerpt():
    data=payload();data['article']['meta_title']='Claude w Barclays';data['article']['meta_description']='Opis wdrożenia.'
    excerpt='meta_title: Claude w Barclays\nmeta_description: Opis wdrożenia.\nlead: Barclays wdraża Claude.'
    checked=validate_output(output(issues=[issue('seo_issue','warning',excerpt)]),data,[])
    assert checked.issues[0].excerpt=='Claude w Barclays' and checked.issues[0].section_heading=='SEO'


@pytest.mark.parametrize('kind,excerpt',[
    ('seo_issue','meta_title: Zmyślony tytuł\nlead: Barclays wdraża Claude.'),
    ('seo_issue','meta_title: Claude w Barclays\nZmyślone zdanie.'),
    ('unsupported_claim','meta_title: Claude w Barclays\nlead: Barclays wdraża Claude.'),
])
def test_labeled_excerpt_never_accepts_invented_or_factual_composites(kind,excerpt):
    from app.services.llm.base import LLMError
    data=payload();data['article']['meta_title']='Claude w Barclays'
    with pytest.raises(LLMError):validate_output(output(issues=[issue(kind,'warning',excerpt)]),data,[])


EDITORIAL_EXCERPT = ('Każdy zakończony epizod przez interfejs OpenEnv zwraca binarny wynik pass/fail. '
    'Adapter zapisuje błędy operacyjne osobno, aby umożliwić ponowienie prób. '
    'Wynik kanoniczny musi je rozwiązać lub jawnie uwzględnić; '
    'w opublikowanych wynikach autorzy zaliczyli błędy systemowe do nieudanych prób.')


def test_editorial_excerpt_recovers_unique_minor_inflection_errors():
    data = payload()
    data['article']['content'] = EDITORIAL_EXCERPT
    quoted = EDITORIAL_EXCERPT.replace('Każdy zakończony', 'Każde zakończone')
    checked = validate_output(output(issues=[issue('style_issue', 'info', quoted)]), data, [])
    assert checked.issues[0].excerpt == EDITORIAL_EXCERPT


@pytest.mark.parametrize('kind,severity,change', [
    ('unsupported_claim', 'info', 'inflection'),
    ('style_issue', 'high', 'inflection'),
    ('style_issue', 'info', 'number'),
    ('style_issue', 'info', 'paraphrase'),
    ('style_issue', 'info', 'ambiguous'),
])
def test_editorial_excerpt_recovery_never_accepts_factual_changes_or_ambiguous_anchors(kind, severity, change):
    from app.services.llm.base import LLMError
    data = payload()
    actual = EDITORIAL_EXCERPT + ' Zapisano 20 prób.'
    data['article']['content'] = actual
    quoted = actual.replace('Każdy zakończony', 'Każde zakończone')
    if change == 'number': quoted = actual.replace('20', '21')
    if change == 'paraphrase': quoted = actual.replace('binarny wynik', 'odpowiedni rezultat')
    if change == 'ambiguous': data['article']['content'] += '\n\n' + actual
    with pytest.raises(LLMError, match='fragment'):
        validate_output(output(issues=[issue(kind, severity, quoted)]), data, [])
