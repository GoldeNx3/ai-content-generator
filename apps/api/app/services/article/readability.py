"""Editorial checks for Polish Markdown, not a replacement for Yoast's language analyzer."""
import re
from markdown_it import MarkdownIt
from app.schemas.qa import QAIssueOutput

READABILITY_GUIDELINES = '''Czytelność i SEO (stosuj bez zmiany faktów):
- Podział nagłówków: celuj w 150–250 słów między H2/H3; nie przekraczaj 300 słów
  bez kolejnego nagłówka. Dłuższy temat podziel przez konkretne H3 według podtematów,
  np. mechanizm, warunek, wynik. Nie skracaj wyjaśnień ani nie dodawaj pustych sekcji.
  H2 to heading sekcji; H3 możesz zapisać jako ### w jej content. Nigdy nie dodawaj H1.
- Akapity zwykle 40–100 słów, najwyżej 150; jeden akapit rozwija jedną myśl.
- Słowa łączące: cel 30–40% zdań z naturalnym wskazaniem relacji między informacjami.
  Dobieraj do sensu: dodanie „również”, „ponadto”; kontrast „jednak”, „natomiast”,
  „z kolei”, „mimo to”; wyjaśnienie „ponieważ”, „dlatego”; przykład „na przykład”;
  kolejność „najpierw”, „następnie”; warunek „jeśli”; porównanie „podobnie”, „w porównaniu”.
  Nie wstawiaj spójników mechanicznie, nie zaczynaj kolejnych zdań tak samo i nie dopisuj
  nieudowodnionego związku przyczynowego. „Dlatego” wymaga uzasadnionego wynikania.
- Większość zdań do 20 słów; cel najwyżej 25% dłuższych zdań. Rozdziel wielokrotnie
  złożone zdania w naturalnym miejscu, zachowując modalność i przypisanie źródła.
  Nazwy techniczne, cytaty i kod zachowaj dokładnie, nawet jeśli są długie.
- Preferuj stronę czynną, gdy znany jest wykonawca. Nie wymyślaj wykonawcy, aby zmienić
  zdanie bierne; stosuj bierną wtedy, gdy uzasadnia ją sens. Unikaj trzech kolejnych zdań
  rozpoczynających się tym samym słowem. Wyjaśniaj potrzebne terminy materiałem źródłowym.
- Focus keyword wybierz z realnego tematu; użyj jej naturalnie w SEO title, leadzie,
  meta description i odpowiednim H2/H3, jeśli oddaje treść. Uwzględnij odmianę i synonimy.
  Bez keyword stuffing i bez wymuszania identycznej frazy w każdym nagłówku.
- SEO title około 50–60 znaków, opis 140–160; pełny sens ważniejszy od sztucznego cięcia.
  Linki wyłącznie do istniejących, udokumentowanych adresów; bez wymyślania internal links.
  Gdy nie ma obrazka, nie dodawaj go dla wyniku SEO. Alt, jeśli istnieje obrazek,
  ma opisywać jego rzeczywistą zawartość, nie być listą fraz. FAQ/HowTo tylko dla realnej struktury.
- Czytelność nie uprawnia do nowych twierdzeń, usuwania ograniczeń researchu ani zmiany
  danych. Nie gwarantuj zielonych kontrolek Yoast; wynik zależy również od języka i konfiguracji.
'''


def readability_issues(lead: str, content: str) -> list[QAIssueOutput]:
    """Count visible prose between actual headings; ignore fenced code and URL destinations."""
    text=lead+'\n\n'+content
    lines=text.splitlines()
    tokens=MarkdownIt('commonmark').enable('table').parse(text)
    issues=[];heading='Lead';words=0;excerpt='';parent=None
    def issue(kind,fragment,reason,suggestion):
        issues.append(QAIssueOutput(type=kind,severity='warning',excerpt=fragment,reason=reason,
            suggestion=suggestion,section_heading=heading,fact_ids=[],source_ids=[],auto_fixable=True))
    def finish():
        if words>300:
            issue('structure_issue',excerpt,f'Rozkład nagłówków: blok „{heading}” ma {words} słów bez kolejnego H2/H3 (zalecane maks. 300).',
                'Podziel blok w miejscu zmiany podtematu przez konkretny H2/H3. Zachowaj fakty i potrzebne wyjaśnienia.')
    for token in tokens:
        if token.type=='heading_open':
            finish();words=0;excerpt='';parent='heading'
        elif token.type=='paragraph_open':parent='paragraph' if not token.hidden else 'list'
        elif token.type=='inline':
            visible=' '.join(child.content for child in (token.children or []) if child.type in ('text','code_inline'))
            if parent=='heading':
                heading=token.content;parent=None;continue
            count=len(re.findall(r'\b[\w]+(?:[-’][\w]+)*\b',visible))
            words+=count
            raw='\n'.join(lines[token.map[0]:token.map[1]]) if token.map else token.content
            if not excerpt:excerpt=raw
            if parent=='paragraph' and count>150:
                issue('style_issue',raw,f'Długość akapitu: {count} słów (zalecane maks. 150).',
                    'Podziel akapit w miejscu zmiany myśli, bez usuwania faktów i bez dopisywania treści.')
            parent=None
    finish()
    return issues
