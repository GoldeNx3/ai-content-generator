# Podgląd artykułu i obsługa aplikacji

Wybrany artykuł ma osobny, zawsze rozwinięty obszar. Nie jest ukryty w karcie generowania. Górna nawigacja „Artykuł” prowadzi bezpośrednio do tekstu; link „Czytaj wybrany tekst” jest także w QA i Auto Fix.

Wybór wersji jest wspólny dla podglądu, QA, Auto Fix i approval. „Najnowsza” oznacza najnowszą wersję w historii, a „zatwierdzona” konkretną wersję zaakceptowaną przez człowieka. Czytanie starszej wersji nie modyfikuje tekstu ani nie wykonuje AI.

- **Czytaj tekst** pokazuje tytuł, lead i cały Markdown. Brief, SEO, statystyki oraz dowody znajdują się w rozwijanym panelu.
- **Historia wersji** pokazuje pochodzenie, wynik QA i status; wybór wiersza otwiera jego tekst i raporty.
- **Kopiuj Markdown** kopiuje wybraną wersję wraz z tytułem i leadem.
- **Edytuj tekst** otwiera formularz dla konkretnej wersji. Zapis tworzy nową wersję i wymaga nowego QA. Praca w tle nie resetuje niezapisanego formularza.
- Karty pipeline’u służą uruchamianiu działań i przeglądaniu raportów. Auto Fix jest dostępny w nagłówku swojej karty, a niedostępne działania mają wyjaśnienie warunków.

Dostępność: polski język dokumentu, link pomijający nawigację, widoczne etykiety filtrów i formularzy, kontekstowe nazwy akcji, nagłówki tabel, fokus klawiatury, komunikaty ładowania oraz ograniczenie animacji przy prefers-reduced-motion. Nawigacja i szerokie tabele przewijają się we własnych obszarach na telefonie.

Filtry listy tematów nie ograniczają globalnego pobierania RSS ani oceny partii. Kolejka zachowuje działanie w tle, retry i historię prób. Żadne z tych zmian UI nie zmienia API, modelu wersji ani reguł QA/approval.

Weryfikacja: testy UI pipeline’u, Auto Fix/Approval i kolejki z mockowanymi API; regresja niezapisanej edycji przy zakończeniu generowania w tle; odczyt czterech rzeczywistych stron w szerokościach 1440 i 390 px oraz podglądu w 768 px; brak przepełnienia, powielonych ID i błędów przeglądarki. Testy rzeczywistych stron nie wysyłają zapisów ani wywołań AI.

### Widoki przestrzeni redakcyjnej

Nawigacja na stronie tematu przełącza osobne widoki: Artykuł, Temat, Ocena tematu, Research, Generowanie, QA oraz Poprawki i zatwierdzenie. Aktywny widok ma wyróżnienie oraz `aria-current`. Link w adresie pozwala otworzyć bezpośrednio wybrany etap; przyciski Wstecz/Dalej przywracają widok. Wybrany etap otwiera raport, bez dodatkowego rozwijania karty.

Domyślny widok Artykuł pokazuje tekst, wybór wersji, wynik QA i następny krok. Zatwierdzenie tematu znajduje się w widoku Temat i jest osobną decyzją od zatwierdzenia wersji artykułu. Panele pozostają zamontowane podczas przełączania: kolejka nadal odświeża status, a rozpoczęta edycja pozostaje zachowana.

### Wspólny układ etapów i kolory

Każdy etap korzysta z `WorkflowSection`: nagłówek z akcją i statusem, wybrany materiał (jeśli dotyczy), objaśnienia „Cel etapu / Warunki uruchomienia / Co dalej”, przebieg zadania, wynik oraz podsumowanie kosztu. Wybór materiału pozostaje widoczny również przy zwiniętym raporcie. Wyjaśnienia są wspólne dla stanów pustych i zakończonych, dostępne pod „Jak działa ten etap?”. Domyślnie są zwinięte, aby wynik pozostał na pierwszym planie.

Zieleń oznacza ukończenie lub gotowość, błękit pracę w toku, bursztyn potrzebę weryfikacji, a czerwień błąd. QA z niezaliczonym wynikiem ma bursztynowy nagłówek nawet po ukończeniu joba. Krytyczne problemy i niepoparte twierdzenia mają dodatkowe wyróżnienia w licznikach raportu. Koszt pozostaje neutralny: płatność sama w sobie nie oznacza ostrzeżenia. Znaczenie koloru zawsze jest również opisane tekstem.
