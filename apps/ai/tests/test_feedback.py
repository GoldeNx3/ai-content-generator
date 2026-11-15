# Rola pliku: Testy pętli zwrotnej redaktora: wycięcie zmienionych fragmentów, prompt z poprawkami i powodami
# odrzuceń, filtrowanie propozycji już obecnych w profilu oraz zasady stylu w pisarzu i QA.

import pytest

from ai.errors import TaskInputError
from app.schemas.editorial import EditorialProfile
from app.schemas.feedback import FeedbackSuggestions
from app.services.feedback.diff import changed_passages
from app.services.llm.base import ArticleContext
from app.services.llm.feedback import build_feedback_prompt
from app.services.llm.qa import QA_SYSTEM_PROMPT
from app.services.llm.writer_prompt import build_writer_prompt
from tests.article_fakes import make_brief

ORIGINAL = ('## Wstęp\n\nW dzisiejszym dynamicznym świecie Laravel 13 to prawdziwa rewolucja.\n\n'
            '## Kolejki\n\nKolejki mają priorytety.\n\n## Podsumowanie\n\nWarto spróbować.')
EDITED = ('## Wstęp\n\nLaravel 13 wyszedł we wtorek.\n\n'
          '## Kolejki\n\nKolejki mają priorytety.\n\n## Podsumowanie\n\nWarto spróbować.')


class FakeFeedback:
    def __init__(self, suggestions):
        self.suggestions = suggestions
        self.prompts = []

    async def suggest(self, prompt):
        self.prompts.append(prompt)
        result = FeedbackSuggestions(suggestions=self.suggestions)
        result._usage = {'model': 'gpt-test', 'input_tokens': 10, 'output_tokens': 5}
        return result


def test_only_changed_passages_are_kept():
    passages = changed_passages(ORIGINAL, EDITED)
    assert passages == [{'before': 'W dzisiejszym dynamicznym świecie Laravel 13 to prawdziwa rewolucja.',
                         'after': 'Laravel 13 wyszedł we wtorek.'}]
    assert changed_passages(ORIGINAL, ORIGINAL) == []


def test_prompt_contains_changes_rejections_and_the_current_profile():
    profile = EditorialProfile(banned_phrases=['game changer'], style_rules=['Zdania do 20 słów.'])
    prompt = build_feedback_prompt('Laravel 13', changed_passages(ORIGINAL, EDITED), ['Za dużo ogólników na początku.'], profile)
    assert 'W dzisiejszym dynamicznym świecie' in prompt and 'Laravel 13 wyszedł we wtorek.' in prompt
    assert 'Za dużo ogólników na początku.' in prompt
    assert '„game changer”' in prompt and 'Zdania do 20 słów.' in prompt


async def test_suggestions_already_in_the_profile_are_dropped():
    from ai.context import TaskContext
    from ai.runtime import run
    ctx = TaskContext()
    ctx._providers = {'feedback': FakeFeedback([
        {'kind': 'banned_phrase', 'text': 'W dzisiejszym dynamicznym świecie', 'why': 'Usuwasz ten wstęp.'},
        {'kind': 'banned_phrase', 'text': 'Game Changer', 'why': 'Już zakazane.'},
        {'kind': 'style_rule', 'text': 'zdania do 20 słów.', 'why': 'Już jest.'},
        {'kind': 'style_rule', 'text': 'Pierwsze zdanie podaje konkretny fakt z datą.', 'why': 'Tak poprawiasz wstępy.'},
    ])}

    response = await run({'task': 'feedback.suggest', 'input': {
        'title': 'Laravel 13', 'original': ORIGINAL, 'edited': EDITED, 'rejections': [],
        'editorial': {'banned_phrases': ['game changer'], 'style_rules': ['Zdania do 20 słów.']}}}, ctx)

    assert response['ok'] is True
    assert [s['text'] for s in response['result']['suggestions']] == [
        'W dzisiejszym dynamicznym świecie', 'Pierwsze zdanie podaje konkretny fakt z datą.']
    assert response['calls'][0]['stage'] == 'learning_feedback'


async def test_nothing_to_learn_from_is_an_input_error():
    from ai.context import TaskContext
    from ai.tasks.feedback import run as suggest
    ctx = TaskContext()
    ctx._providers = {'feedback': FakeFeedback([])}
    with pytest.raises(TaskInputError):
        await suggest({'title': 'T', 'original': ORIGINAL, 'edited': ORIGINAL, 'rejections': []}, ctx)


async def test_demo_mode_suggests_without_cost():
    from ai.runtime import run
    response = await run({'task': 'feedback.suggest', 'demo': True, 'input': {
        'title': 'T', 'original': ORIGINAL, 'edited': EDITED, 'rejections': []}})
    assert response['ok'] is True and response['result']['suggestions']
    assert response['calls'][0]['estimated_cost_usd'] in ('0.000000', None) or float(response['calls'][0]['estimated_cost_usd']) == 0


def test_banned_phrase_suggestions_respect_the_profile_limit():
    from pydantic import ValidationError
    from app.schemas.feedback import StyleSuggestion
    with pytest.raises(ValidationError):
        StyleSuggestion(kind='style_rule', text='a' * 201, why='w')


def test_writer_and_qa_follow_the_accepted_style_rules():
    context = ArticleContext(candidate_title='T', candidate_source='S', published_at=None, research_summary='s',
        why_it_matters='w', suggested_angle='a', facts=[], sources=[], uncertainties=[], conflicts=[], article_type='news',
        type_guide='g', length_hint='l', angle=None, instructions=None, article_format='news',
        editorial=EditorialProfile(style_rules=['Pierwsze zdanie podaje konkretny fakt z datą.']).model_dump())
    prompt = build_writer_prompt(context, make_brief([1]))
    assert 'ZASADY STYLU' in prompt and 'Pierwsze zdanie podaje konkretny fakt z datą.' in prompt
    assert 'style_rules' in QA_SYSTEM_PROMPT
