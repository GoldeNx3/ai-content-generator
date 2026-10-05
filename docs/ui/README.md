# Przestrzeń redakcyjna Content Engine

## Układ

Sześć widoków: Temat, Ocena tematu, Research, Generowanie, QA / jakość, Poprawki i zatwierdzenie. Domyślnie otwiera się Temat; link w adresie pozwala wejść bezpośrednio do etapu. Dotychczasowe linki `#article-workspace` i odnośniki do sekcji tekstu otwierają Generowanie. Wstecz/Dalej przywracają widok.

`WorkflowSection` (eksportowany również jako `PipelineStageLayout`) odpowiada za wspólny nagłówek, status, główną zawartość i timeline oraz sidebar z trzema sekcjami: akcja, pomoc, koszt. Desktop: elastyczna główna kolumna i 390 px panelu. Tablet/telefon: sidebar pod wynikiem. Stepper na telefonie zmienia się w wybór „Etap n z 6” z paskiem postępu.

Stepper odbiera statusy od zamontowanych paneli przez `PipelineStateProvider`. Nie pobiera drugiego zestawu danych i nie ustanawia nowych reguł procesu. Można podejrzeć etapy oczekujące; ich działania są blokowane przez istniejące warunki dostępności. Przykładowo ocena nie jest wymagana do Research, a osobne zatwierdzanie Research nie istnieje w API.

## Dane i działania

| Etap | Główna zawartość | Akcja |
| --- | --- | --- |
| Temat | Materiał RSS, opis, źródło, data, typ | Zatwierdź lub pomiń temat |
| Ocena | Rzeczywista punktacja i cztery kryteria backendu, uzasadnienie | Uruchom ocenę lub przejdź do Research |
| Research | Wszystkie źródła, fragmenty pobranych treści, fakty z referencjami, niepewności i konflikty | Uruchom / ponów analizę lub przejdź do generowania |
| Generowanie | Pełny tekst, wersja, podgląd, Markdown, SEO, historia | Generuj nową wersję lub przejdź do QA |
| QA | Wynik, pięć punktacji, liczniki, karty problemów | Uruchomienie QA lub przejście do etapu poprawek i zatwierdzenia |
| Poprawki | Wyniki każdego fixa, rozwinięty diff, końcowe QA i finalny tekst | Zatwierdzenie konkretnej wersji, odrzucenie lub edycja |

Nie dodano publikowania, keyword API, dodatkowych kryteriów ocen ani prognoz kosztów nieobecnych w danych. Model jest wyświetlany z konfiguracji, zużycie i koszt ze zapisanych danych. Nieznane wartości są oznaczone jako brak danych. Szczegółowe stawki i historia wywołań pozostają dostępne po rozwinięciu.

## Wersje, QA i Auto Fix

Wybór wersji jest wspólny dla podglądu, QA, Auto Fix i approval. Zapis ręczny tworzy nową wersję i wymaga nowego QA. Formularz pozostaje przypięty do wersji źródłowej także podczas pracy zadań w tle. Przełączanie widoków nie odmontowuje paneli ani nie resetuje edycji.

Auto Fix jest dostępny wyłącznie w etapie „Poprawki i zatwierdzenie”, zgodnie z warunkami: ukończone aktualne QA, wspierane problemy auto-fixable, wolna kolejka i pozostała iteracja. Przejście z QA do poprawek tylko zmienia widok. Dopiero kliknięcie Auto Fix używa istniejącego endpointu i uruchamia zadanie. Worker tworzy wersję; jej QA uruchamiasz osobno; ostatni ekran pokazuje wynik bez konieczności ręcznego przechodzenia do QA. Approval nadal wymaga aktualnego QA passed i dotyczy konkretnej wersji. Zatwierdzenie tematu to osobna decyzja.

## Statusy i dostępność

Lista tematów i jej filtr używają wspólnego statusu procesu: Opublikowane, Draft, Zaplanowane, Zatwierdzony, Oczekuje lub Pominięty. Ostatni potwierdzony stan WordPress ma pierwszeństwo. Bez wysyłki do WP status zależy od bieżącej wersji artykułu i decyzji o temacie. Zaliczenie QA nie zatwierdza wersji. Udany, zweryfikowany zapis WordPress oznacza temat jako zatwierdzony w tej samej transakcji co wynik zadania. Nieudana wysyłka nie nadaje statusu publikacji.

Zieleń: zakończony sukces. Etap poprawek po zaliczonym QA czeka na decyzję i jest bursztynowy; staje się zielony po ręcznym zatwierdzeniu. Błękit: queued/running. Bursztyn: wymaga działania. Czerwień: błąd/krytyczny problem. Kolor ma także opis tekstowy i ikonę. Raport QA z problemami ma bursztynowy stan mimo zakończenia joba.

Polski język dokumentu, etykiety formularzy, fokus klawiatury, `aria-current=step`, link pomijający nawigację, zredukowane animacje i responsywne tabele. Panele zadań pokazują status i czas; ID jobów, próby i wywołania są ukryte pod „Szczegóły techniczne”.

## Weryfikacja

`ui-check.mjs`: generowanie, kolejka, stany QA, retry, powrót do tekstu, Markdown i edycja odporna na równoległe zakończenie Write/QA. `auto-fix-ui-check.mjs`: QA → Auto Fix → nowa wersja → nowe QA → approval i ręczna edycja, przy mockowanych API. `candidate-navigation-live-check.mjs`: sześć prawdziwych etapów, wspólny sidebar, desktop/tablet/mobile, podgląd/SEO/historia, Wstecz/Dalej, brak powielonych ID i zero zapisów API. Testy nie wywołują modeli AI.
