# Rola pliku: Testy deterministycznej kontroli liczb w QA: kwoty, procenty, duże liczby i daty muszą występować
# w faktach, źródłach albo „Naszym zdaniu”; numery wersji, bieżący rok, kod, linki i nagłówki są pomijane.

import inspect
from datetime import date

from app.services.qa.numbers import unverified_number_issues

FACT = 'Plan Pro kosztuje 49 USD miesięcznie, a sprzedaż wzrosła o 12,5%.'
SOURCE = 'W 2025 roku firma miała 1 200 klientów i 1,5 mln użytkowników. Premiera odbyła się 2026-11-15.'


def snapshot(content: str, lead: str = 'Lead bez liczb.', take: str | None = None) -> dict:
    return {'article': {'lead': lead, 'content': content}, 'brief': {'editor_take': take},
            'research': {'facts': [{'id': 1, 'claim': FACT}], 'sources': [{'id': 7, 'content': SOURCE}, {'id': 8, 'content': None}]}}


def test_numbers_backed_by_facts_and_sources_pass_in_any_notation():
    content = ('## Ceny\n\nPlan Pro to $49 na miesiąc, wzrost wyniósł 12.5 procent. Firma ma 1200 klientów '
               'i 1.5 million użytkowników, a premiera była 2026-11-15.')
    assert unverified_number_issues(snapshot(content)) == []


def test_an_invented_number_is_flagged_with_its_sentence_and_section():
    issues = unverified_number_issues(snapshot('## Wyniki\n\nSprzedaż wzrosła o 47%. Plan Pro kosztuje 49 USD.'))
    assert len(issues) == 1
    issue = issues[0]
    assert issue.type == 'unverified_number'
    assert issue.severity == 'warning' and issue.auto_fixable is True
    assert issue.excerpt == 'Sprzedaż wzrosła o 47%.'
    assert issue.section_heading == 'Wyniki'
    assert '47%' in issue.reason


def test_versions_years_small_numbers_code_links_and_headings_are_ignored():
    year = date.today().year
    content = (f'## 3 sposoby na Laravel 13\n\nLaravel 13 i PHP 8.4 działają z GPT-5 oraz v2.1. W {year} i {year - 1} roku '
               'zespół miał 3 osoby. Kod `port 8080` i [link](https://example.com/post/12345).\n\n'
               '```bash\nsleep 300\n```\n\n> Cytat z 999 osobami.')
    assert unverified_number_issues(snapshot(content)) == []


def test_editor_take_numbers_count_as_confirmed():
    content = 'Używamy tego w 14 projektach.'
    assert unverified_number_issues(snapshot(content)) != []
    assert unverified_number_issues(snapshot(content, take='Używamy tego w 14 projektach od roku.')) == []


def test_the_lead_is_checked_and_issues_are_capped():
    assert unverified_number_issues(snapshot('Treść.', lead='Firma zatrudnia 350 osób.'))[0].excerpt == 'Firma zatrudnia 350 osób.'
    many = ' '.join(f'Wartość {n} sztuk.' for n in range(100, 130))
    assert len(unverified_number_issues(snapshot(many))) == 10


def test_qa_task_runs_the_number_check_and_auto_fix_accepts_it():
    import ai.tasks.qa as qa_task
    from app.schemas.qa import QAIssueType
    from app.services.auto_fix.validation import ALLOWED
    assert 'unverified_number_issues' in inspect.getsource(qa_task)
    assert QAIssueType('unverified_number')
    assert 'unverified_number' in ALLOWED
