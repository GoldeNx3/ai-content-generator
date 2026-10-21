from app.services.article.readability import readability_issues


def test_long_section_detected_and_real_h3_resets_count():
    paragraph=' '.join(['słowo']*155)
    text='## Mechanizm\n\n'+paragraph+'\n\n'+paragraph
    issues=readability_issues('',text)
    assert any('310' in i.reason and i.type=='structure_issue' for i in issues)
    assert not readability_issues('',text.replace('\n\n'+paragraph,'\n\n### Warunek\n\n'+paragraph,1).replace(paragraph,' '.join(['słowo']*100)))


def test_paragraph_warning_has_literal_excerpt_and_can_be_fixed():
    text=' '.join(['fakt']*151)
    issues=readability_issues('', '## Wynik\n\n'+text)
    assert len(issues)==1 and issues[0].excerpt==text and issues[0].auto_fixable


def test_code_headings_do_not_split_prose_and_code_does_not_create_warnings():
    assert not readability_issues('', '## Kod\n\n```text\n'+('kod '*400)+'\n### To nie nagłówek\n```')
    text=('opis '*155).strip()
    issues=readability_issues('',f'## Sekcja\n\n{text}\n\n```text\n### Kod\n```\n\n{text}')
    assert any(i.type=='structure_issue' for i in issues)


def test_lead_and_conclusion_checked_and_links_count_visible_text():
    assert readability_issues(' '.join(['lead']*151),'## Sekcja\n\nKrótko.')[0].section_heading=='Lead'
    assert not readability_issues('', '## Sekcja\n\n[Dokumentacja](https://example.test/'+('url'*400)+')')


def test_generation_warns_about_long_output_before_qa():
    from tests.article_fakes import make_output
    from app.services.article.validation import validate_writer_output
    from app.services.llm.base import FactInput
    from app.schemas.article import WriterSection
    output=make_output([1,2],[1],sections=[WriterSection(heading='Mechanizm',content=' '.join(['opis']*301),used_fact_ids=[1],source_ids=[1])])
    facts=[FactInput(id=1,claim='Fakt.',importance='critical',confidence=100,source_ids=[1]),FactInput(id=2,claim='Fakt drugi.',importance='important',confidence=100,source_ids=[1])]
    checked=validate_writer_output(output,facts,{1},[],[])
    assert any('Rozkład nagłówków' in warning for warning in checked.warnings)
