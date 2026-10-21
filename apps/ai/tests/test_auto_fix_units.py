from copy import deepcopy
import pytest
from app.schemas.auto_fix import FixOutput
from app.services.auto_fix.validation import apply_fixes
from app.services.jobs.errors import JobInputError


def payload(kind='unsupported_claim', field='content', text='Wzrost o 47%.'):
    return {'article': {'title': 'Tytuł', 'lead': 'Lead', 'content': text, 'slug': 'tytul',
        'meta_title': 'Tytuł', 'meta_description': 'Opis'},
        'issues': [dict(id=41, type=kind, auto_fixable=True, excerpt=text, fact_ids=[12], source_ids=[4])],
        'research': {'facts': [dict(id=12,claim='Cena wynosi 10 USD.',source_ids=[4])],
            'sources':[dict(id=4)], 'uncertainties':[], 'conflicts':[]}}


def output(field='content', before='Wzrost o 47%.', after='', **extra):
    patch=dict(field=field,before=before,after=after,qa_issue_ids=[41],fact_ids=[],source_ids=[])
    patch.update(extra)
    return FixOutput(summary='Minimalna poprawka.', patches=[patch],
        fix_results=[dict(qa_issue_id=41,status='fixed',reason='Usunięto błąd.')])


@pytest.mark.parametrize('kind,field,before,after', [
    ('unsupported_claim','content','Wzrost o 47%.',''),
    ('title_mismatch','title','Tytuł','Nowy tytuł'),
    ('repetition','content','Lead. Lead.','Lead.'),
    ('incorrect_number','content','Cena wynosi 47 USD.','Cena wynosi 10 USD.'),
])
def test_minimal_patch(kind,field,before,after):
    data=payload(kind,field,before);data['article'][field]=before
    patch=output(field,before,after,fact_ids=[12] if kind=='incorrect_number' else [],
        source_ids=[4] if kind=='incorrect_number' else [])
    result=apply_fixes(data,patch,.35)
    assert result.article[field]==after
    for name,value in data['article'].items():
        if name!=field: assert result.article[name]==value


@pytest.mark.parametrize('override', [dict(fact_ids=[999]),dict(source_ids=[999]),dict(qa_issue_ids=[999])])
def test_invalid_ids_are_rejected(override):
    with pytest.raises(JobInputError): apply_fixes(payload(),output(**override),.35)


def test_uncertain_number_skipped_and_all_skipped_no_changes():
    data=payload('incorrect_number')
    response=FixOutput(summary='Brak danych.',patches=[],fix_results=[dict(qa_issue_id=41,status='skipped',reason='Brak pewnej wartości.')])
    result=apply_fixes(data,response,.35)
    assert result.article==data['article'] and result.change_ratio==0


def test_conflicts_cannot_be_fixed():
    with pytest.raises(JobInputError): apply_fixes(payload('ignored_conflict'),output(),.35)


def test_number_needs_research_evidence():
    with pytest.raises(JobInputError): apply_fixes(payload('incorrect_number'),output(after='Wzrost o 10%.'),.35)


def test_large_diff_warns_without_blocking():
    result=apply_fixes(payload(),output(after='Nowy akapit. '*20),.35)
    assert result.change_ratio>.35 and result.warnings


def test_missing_duplicate_results_and_unmatched_patch_rejected():
    response=output();response.fix_results=[]
    with pytest.raises(JobInputError): apply_fixes(payload(),response,.35)
    response=output(before='Nie ma takiego fragmentu')
    with pytest.raises(JobInputError): apply_fixes(payload(),response,.35)

def test_patch_must_correspond_to_issue():
    data=payload()
    with pytest.raises(JobInputError): apply_fixes(data,output('title','Tytuł','Niepowiązana zmiana'),.35)


def test_date_with_evidence():
    data=payload('incorrect_date',text='Premiera w 2025.');data['research']['facts'][0]['claim']='Premiera w 2026.'
    fixed=apply_fixes(data,output(before='Premiera w 2025.',after='Premiera w 2026.',fact_ids=[12],source_ids=[4]),.35)
    assert fixed.article['content']=='Premiera w 2026.'
