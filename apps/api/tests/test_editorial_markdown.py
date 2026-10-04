import pytest

from app.services.article.composition import count_words, sanitize_output
from app.services.article.validation import validate_writer_output
from app.services.research.content_budget import truncate_text
from app.services.research.content_extractor import ContentExtractor
from tests.article_fakes import make_output

CODE = 'def greet(name):\n    if name:\n        return f"Hi {name}"\n'
HTML = '<article><h1>Migration</h1><p>' + 'Instructions and prerequisites for migration. ' * 10 + (
    '</p><pre><code class="language-python">' + CODE + '</code></pre>'
    '<p>Run <code>npm install</code>.</p>'
    '<table><tr><th>Model</th><th>Price</th></tr><tr><td>A</td><td>10 USD</td></tr></table></article>')


@pytest.mark.parametrize('fallback', [False, True])
def test_source_code_and_tables_keep_their_structure(monkeypatch, fallback):
    if fallback:
        monkeypatch.setattr('app.services.research.content_extractor.trafilatura.extract', lambda *a, **kw: None)
    document = ContentExtractor.extract_from_html(HTML, 'https://example.com/docs')
    assert '```python\n' + CODE.rstrip('\n') + '\n```' in document.content
    assert '`npm install`' in document.content
    assert '| Model | Price |' in document.content
    assert '| A | 10 USD |' in document.content


def test_sanitizing_references_does_not_corrupt_code_examples():
    code = '```python\nlabel = "[FACT #999]"\n```\n\nInline `[FACT #998]`.'
    output = make_output([1, 2], [1])
    output.sections[0].content = code + '\n\nZdanie [FACT #1].'
    cleaned = sanitize_output(output)
    assert code in cleaned.sections[0].content
    assert 'Zdanie [FACT #1]' not in cleaned.sections[0].content
    assert 999 not in cleaned.sections[0].used_fact_ids
    assert 998 not in cleaned.sections[0].used_fact_ids


def test_source_budget_never_sends_a_partial_code_example():
    text = 'Wprowadzenie.\n\n```python\n' + CODE * 20 + '\n```\n\nDalszy opis.'
    trimmed = truncate_text(text, 160)
    assert '```' not in trimmed
    assert len(trimmed) <= 160


def test_code_does_not_inflate_prose_word_count():
    assert count_words('Dwa słowa.\n\n```python\n' + CODE * 20 + '\n```') == 2


def test_editorial_validation_flags_repetition_and_missing_code_language():
    output = make_output([1, 2], [1])
    paragraph = 'Nowa wersja zmienia sposób migracji istniejącego projektu i wymaga sprawdzenia ustawień przed uruchomieniem aplikacji.'
    output.sections[0].heading = 'Co się wydarzyło'
    output.sections[0].content = paragraph + '\n\n```\nnpm install\n```'
    output.sections[1].heading = 'Dlaczego to ważne'
    output.sections[1].content = paragraph
    validated = validate_writer_output(output, [], {1}, [], [])
    assert any('języka' in warning for warning in validated.warnings)
    assert any('powtórzony akapit' in warning.lower() for warning in validated.warnings)
    assert any('szablonowe nagłówki' in warning.lower() for warning in validated.warnings)


def test_code_strings_are_not_misclassified_as_editorial_filler():
    output = make_output([1, 2], [1])
    output.sections[0].content = '```python\nprint("warto zauważyć")\n```'
    validated = validate_writer_output(output, [], {1}, [], [])
    assert not any('warto zauważyć' in warning for warning in validated.warnings)


def test_structure_history_is_only_form_metadata():
    from app.services.article.editorial import describe_structure
    article = make_output([1, 2], [1])
    article.sections[0].content = 'Tajny fakt.\n\n```python\nprint(42)\n```'
    article.sections[1].content = '| A | B |\n| --- | --- |\n| 1 | 2 |'
    structure = describe_structure([{'heading': s.heading} for s in article.sections], '\n\n'.join(s.content for s in article.sections))
    assert structure['code_blocks'] == 1
    assert structure['tables'] == 1
    assert 'Tajny fakt' not in str(structure)
    assert 'print' not in str(structure)


def test_prompt_plans_form_without_forcing_every_article_into_a_table():
    from app.services.llm.writer_prompt import BRIEF_SYSTEM_PROMPT, WRITER_SYSTEM_PROMPT
    assert 'presentation' in BRIEF_SYSTEM_PROMPT
    assert 'Nie zaczynaj każdego planu' in BRIEF_SYSTEM_PROMPT
    assert 'składni GFM' in WRITER_SYSTEM_PROMPT
    assert 'Nie stosuj tabel' in WRITER_SYSTEM_PROMPT
    assert 'Nie wymyślaj API' in WRITER_SYSTEM_PROMPT


def test_paragraph_boundary_cannot_reopen_a_complete_code_block():
    text = 'Intro.\n\n```python\n' + 'x' * 100 + '\n\ny = 2\n```\n' + 'trailing ' * 30
    trimmed = truncate_text(text, 158)
    from app.services.markdown import fences
    assert all(block.closed for block in fences(trimmed))


async def test_recent_structure_is_frozen_for_queued_writer(session):
    from dataclasses import asdict, replace
    from pydantic import TypeAdapter
    from app.core.config import get_settings
    from app.schemas.article import GenerateArticleRequest
    from app.services.article.write import ArticleService
    from app.services.jobs.service import JobService
    from app.services.llm.base import ArticleContext
    from app.services.llm.cost import LLMCostCalculator
    from app.services.llm.writer_prompt import build_brief_prompt
    from tests.article_fakes import FakeArticleLLM, research_fixture
    candidate, _ = await research_fixture(session)
    article = await ArticleService(session, FakeArticleLLM(), LLMCostCalculator({})).generate(candidate.id, GenerateArticleRequest())
    await session.refresh(candidate, ['source'])
    payload = await JobService(session, get_settings())._payload('write', candidate, {})
    frozen = TypeAdapter(ArticleContext).validate_python(payload['context'])
    assert frozen.recent_structures[0]['headings'] == [s['heading'] for s in article.sections if s.get('heading')]
    assert 'OSTATNIE FORMY TEKSTÓW' in build_brief_prompt(frozen)
    old_payload = asdict(replace(frozen, recent_structures=[]))
    old_payload.pop('recent_structures')
    assert TypeAdapter(ArticleContext).validate_python(old_payload).recent_structures == []


def test_merged_source_table_preserves_value_associations(monkeypatch):
    html = '<article><p>' + 'Opis wariantów cenowych. ' * 20 + '</p><table><tr><th>Model</th><th>Plan</th><th>Price</th></tr><tr><td rowspan="2">A</td><td>Basic</td><td>10</td></tr><tr><td>Pro</td><td>20</td></tr></table></article>'
    document = ContentExtractor.extract_from_html(html, 'https://example.com/pricing')
    assert '| A | Pro | 20 |' in document.content


def test_source_colspan_expands_shared_heading():
    html = '<article><p>' + 'Opis wariantów cenowych. ' * 20 + '</p><table><tr><th>Model</th><th colspan="2">Plans</th></tr><tr><td>A</td><td>Basic</td><td>Pro</td></tr></table></article>'
    document = ContentExtractor.extract_from_html(html, 'https://example.com/pricing')
    assert '| Model | Plans | Plans |' in document.content
    assert '| A | Basic | Pro |' in document.content


@pytest.mark.parametrize('fallback', [False, True])
def test_code_inside_figure_is_not_removed_as_decoration(monkeypatch, fallback):
    if fallback:
        monkeypatch.setattr('app.services.research.content_extractor.trafilatura.extract', lambda *a, **kw: None)
    html = HTML.replace('<pre>', '<figure class="code-example"><pre>').replace('</pre>', '</pre></figure>')
    document = ContentExtractor.extract_from_html(html, 'https://example.com/docs')
    assert '```python\n' + CODE.rstrip('\n') + '\n```' in document.content


def test_excessively_large_table_is_omitted_without_expanding_it():
    html = '<article><p>' + 'Opis tabeli źródłowej. ' * 20 + '</p><table><tr><th>Model</th></tr>' + '<tr><td>A</td></tr>' * 300 + '</table></article>'
    document = ContentExtractor.extract_from_html(html, 'https://example.com/data')
    assert 'Tabela pominięta' in document.content
    assert len(document.content) < 1000


@pytest.mark.parametrize('cells,rows', [(100, 1000), (100, 100)])
def test_span_amplification_is_bounded(cells, rows):
    html = '<article><p>' + 'Opis tabeli źródłowej. ' * 20 + '</p><table><tr>' + f'<td colspan="100" rowspan="{rows}">X</td>' * cells + '</tr>' + '<tr></tr>' * (rows-1) + '</table></article>'
    document = ContentExtractor.extract_from_html(html, 'https://example.com/data')
    assert 'Tabela pominięta' in document.content
    assert len(document.content) < 1000


def test_single_oversized_colspan_is_not_silently_relabelled():
    html = '<article><p>' + 'Opis tabeli źródłowej. ' * 20 + '</p><table><tr><td colspan="1000000">X</td></tr></table></article>'
    document = ContentExtractor.extract_from_html(html, 'https://example.com/data')
    assert 'Tabela pominięta' in document.content


def test_merged_cell_text_cannot_amplify_without_a_character_budget():
    html = '<article><p>' + 'Opis tabeli źródłowej. ' * 20 + '</p><table><tr><td colspan="100" rowspan="100">' + 'Value' * 40 + '</td></tr>' + '<tr></tr>' * 99 + '</table></article>'
    document = ContentExtractor.extract_from_html(html, 'https://example.com/data')
    assert 'Tabela pominięta' in document.content
    assert len(document.content) < 1000
