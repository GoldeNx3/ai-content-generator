# Demo pipeline bez kosztów AI

```bash
make dev       # albo make up, jeśli środowisko już jest skonfigurowane
make migrate
make seed-demo
```

Seeder zapisuje syntetyczne dane Nexa w tej samej bazie co aplikacja. Nie korzysta z AI, sieci ani kluczy API. `make seed` nadal dodaje normalne źródła RSS. `make seed-demo` tworzy osobne, nieaktywne źródło `[DEMO] Scenariusze pipeline — 0 kosztów AI`. Na liście tematów wybierz je w filtrze **Źródło**. Seeder wypisuje także bezpośrednie linki do wszystkich przypadków.

Uruchamiaj demo z aktualnym API i workerem. Po aktualizacji kodu uruchom `docker compose restart api worker scheduler`, aby procesy załadowały obsługę demo. Pierwsze uruchomienie zapisuje brakujące przypadki atomowo; kolejne zachowują prawdziwe dane i zmiany wykonane przez użytkownika. Seeder nie resetuje scenariuszy.

## Dwa sposoby użycia

**Interaktywnie:** otwórz `[DEMO 01] Zacznij tutaj — cały interaktywny flow`. Możesz klikać normalne przyciski aplikacji. Requesty zwracają 202, pracę wykonuje worker, powstają prawdziwe rekordy i historia wersji. Dostawcy demo zwracają fikcyjne odpowiedzi lokalnie. Nie jest potrzebny klucz OpenAI. Koszty i tokeny wynoszą 0. Ochrona jest oparta na zapisanym adresie Candidate w zarezerwowanej domenie `demo.content-engine.invalid`; klient nie może włączyć demo dla zwykłego tematu przez flagę requestu. Zwykłe tematy nadal korzystają z rzeczywistych usług i mogą kosztować.

**Przegląd stanów:** pozostałe scenariusze mają już raporty i wersje. Przykłady opisane jako „migawka” celowo pozostają queued/running: worker ich nie podejmuje, a aktywne zadanie pokazuje blokadę równoległych akcji. Na pozostałych przypadkach można wykonywać działania demo, np. ponowić failed QA, poprawić unsupported claim lub zatwierdzić gotową wersję. Przykładowe raporty są fixture, a nie wynikiem rzeczywistego modelu; symulator jest deterministyczny i nie udaje pełnego fact checkera dowolnego tekstu.

## Przejście krok po kroku

1. Otwórz scenariusz 01 i kliknij **Oceń temat**. Powstanie zadanie classify oraz ocena tematu. Możesz zatwierdzić temat, ale nie jest to approval artykułu.
2. Kliknij **Uruchom research**. Po workerze zobaczysz źródła, fakty, ich powiązania, niepewności i konflikty.
3. Kliknij **Generuj artykuł** i potwierdź opcje. Jedno zadanie wykonuje Brief, potem Write. Powstaje v1, bez QA i bez approval.
4. W karcie QA sprawdź **wybraną wersję** i kliknij **Run QA**. Demo Writer celowo dodaje „Nexa zwiększa produktywność o 47%.”, którego nie ma w Research. QA zgłosi high unsupported_claim; wynik nie przekroczy 75.
5. Teraz **Auto Fix** jest dostępny w nagłówku karty **Auto Fix + Approval**. Kliknij go: wynik zapisze poprawione/pominięte issue, powstanie v2 z parent=v1, a QA v2 zostanie automatycznie dodane do kolejki. Przycisk „Otwórz nową wersję” pozwala ją wybrać. v1 pozostaje bez zmian.
6. Po nowym QA v2 dostanie ready_for_approval, jeśli spełnia wymagania. Kliknij **Zatwierdź wersję**. Zatwierdzisz wyłącznie tę wersję; nic nie zostanie opublikowane.
7. Wykonaj **Edytuj tekst** i zapisz zmianę: powstanie kolejna wersja draft, która wymaga nowego QA. Stary raport pozostaje przy starej wersji.

## Co robi każdy etap i jakie ma warunki

| Etap | Wejście i działanie | Warunki / rezultat |
|---|---|---|
| 1. Discover | RSS zapisuje Candidate: tytuł, opis, oryginalny URL, źródło i datę. Demo dostarcza je przez seeder. | Aktywne źródło RSS dla normalnego pobierania. Nie tworzy artykułu i nie używa AI. |
| 2. Classify | Ocenia trafność 40%, aktualność 20%, potencjał wyszukiwań 25%, potencjał komercyjny 15%, przypisuje kategorię i uzasadnienie. | Istniejący Candidate, wolna kolejka tematu. Klasyfikacja nie jest obowiązkowym warunkiem Research. Ocena i decyzja zatwierdź/pomiń temat to osobne rzeczy. |
| 3. Research | Zbiera i analizuje materiały; zapisuje ResearchSources, ResearchFacts, confidence, niepewności i konflikty. | Istniejący Candidate i wolna kolejka. Research completed z co najmniej jednym faktem pozwala generować tekst. Nowy research może zmienić bieżące materiały, ale stare wersje zachowują swoje snapshoty. |
| 4. Brief | Plan: kąt, odbiorca, wymagane i opcjonalne fakty, sekcje, długość, braki dowodów. | Ukończony Research i fakty. W UI jest częścią wspólnej karty generowania, a w workerze osobnym krokiem zadania write. |
| 5. Write | Pisze artykuł zgodnie z briefem i tworzy nową wersję z referencjami oraz snapshotem dowodów. | Ukończony Research, wolna kolejka, poprawne opcje. Nowa wersja draft nie ma ważnego QA ani approval. Regenerowanie zachowuje poprzedni tekst. |
| 6. QA | Porównuje konkretną wersję ze snapshotem Research i briefem. Kontroluje twierdzenia, liczby, daty, cytaty, referencje, niepewności, konflikty, styl, strukturę, title/meta/slug. | Snapshot z faktami i źródłami, wolna kolejka. Bez internetu i nowego researchu. Report musi być completed i jego hash musi pasować do wersji. Backend liczy wynik i readiness. |
| 7. Auto Fix | Minimalne poprawki wybranych problemów; bez nowych faktów, własnej wiedzy i researchu. | Najnowsze ukończone i aktualne QA, issue auto-fixable, pozostała iteracja, wolna kolejka. Nowa wersja + wyniki fixed/skipped zapisują się spójnie, po czym automatycznie kolejkuje się jej QA. |
| 7. Human Approval | Człowiek zatwierdza lub odrzuca konkretny ArticleVersion. | Approve wymaga aktualnego QA passed i gotowości wersji. Warnings nie muszą blokować. Nowe approval zastępuje poprzednie approved przez superseded. Reject zapisuje opcjonalny powód. Brak publikacji. |

UI łączy Brief + Write w jedną kartę, dlatego numeracja kart może różnić się od siedmiu logicznych etapów. W karcie QA jest wybór wersji i informacja, której wersji dotyczy raport.

## QA passed, readiness i Auto Fix

Backend zaokrągla `factual×0.40 + source×0.20 + style×0.15 + structure×0.15 + SEO×0.10`. Critical ogranicza wynik do 60; high unsupported_claim do 75. `QA_PASS_SCORE` domyślnie 85. Passed wymaga:

```text
overall_score >= pass_score
critical_issue_count == 0
unsupported_claims_count == 0
```

To odblokowuje **ready_for_approval**, a nie publikację. Sam wynik 90 przy niepopartym fakcie nadal nie daje passed.

Auto Fix nie jest uruchamiany automatycznie po niskim wyniku. Dostępność wynika z **issue**, nie z liczby punktów. Obsługiwane typy: unsupported_claim, title_mismatch, repetition, style_issue, structure_issue, seo_issue, overclaim. incorrect_number i incorrect_date tylko z jednoznacznym poprawnym faktem w Research. Flaga `auto_fixable` jest konieczna, ale backend dodatkowo sprawdza typ, dowody, ID, fragment poprawki i zakres zmian. Cytaty, sprzeczności i niebezpieczne konflikty wymagają weryfikacji ręcznej. Issue może być skipped, jeśli poprawka nie jest bezpieczna.

Po Auto Fix obowiązkowo powstaje nowe QA. Gdy wszystkie poprawki są skipped i tekst się nie zmienił, nie powstaje zbędna nowa wersja ani QA. `AUTO_FIX_MAX_ITERATIONS` domyślnie 2 ogranicza zakończone próby w historii tej gałęzi; techniczne retry zadania nie jest osobną zakończoną iteracją. Po nieudanym QA i wyczerpaniu limitu: manual_review_required. Kolejny Auto Fix wymaga kliknięcia, nie ma nieskończonej pętli. Zmiana ponad `AUTO_FIX_MAX_CHANGE_RATIO` (domyślnie 0.35) może zapisać warning; poważne poprawki struktury nie są przez to automatycznie blokowane.

## Kolejka i wersje

- `queued`: zapisane, czeka na workera; `running`: worker pracuje; `retrying`: automatyczne ponowienie po błędzie przejściowym; `succeeded`: rezultat zapisany; `failed`: błąd końcowy, możliwy ręczny retry.
- Status zadania nie jest statusem artykułu. QA i Fix mają własne pending/running/completed/failed.
- Dla jednego Candidate dopuszczone jest jedno aktywne zadanie. Duplikat z tym samym Idempotency-Key zwraca istniejące zadanie; drugi niezależny request może otrzymać konflikt.
- QA jest przypięte do ID wersji i zamrożonego wejścia. Hash niepasujący do tekstu oznacza stale i blokuje użycie starego raportu do fix/approval.
- Manual edit, regenerowanie i Auto Fix tworzą nową wersję. Historyczne wersje i QA pozostają dostępne. Nowa treść wymaga nowego QA.

## Katalog scenariuszy

Numery odpowiadają prefiksom `[DEMO NN]` na liście tematów. Źródło i nazwy pozwalają szybko je odnaleźć. Linki z konkretnymi ID wypisuje seeder.

| Nr | Scenariusz | Co sprawdzić |
|---|---|---|
| 01 | `discovered` — Zacznij tutaj — cały interaktywny flow | Kliknij ocenę, Research, generowanie, QA, Auto Fix i Approval. Writer celowo dodaje niepoparte 47%; Auto Fix usuwa zdanie, a nowe QA przechodzi. Wszystkie akcje demo są bezpłatne. |
| 02 | `classified` — Ocena tematu — gotowy do Research | Ocena pomaga wybrać temat. Zatwierdzenie tematu nie jest zatwierdzeniem tekstu. Research można uruchomić także bez klasyfikacji. |
| 03 | `ignored` — Temat pominięty | Decyzja redakcyjna ignored nie usuwa historii; możesz przywrócić temat do oczekujących. |
| 04 | `research-queued` — Research czeka w kolejce | Migawka stanu queued: request już zakończony, worker jeszcze nie rozpoczął. To nieruchomy przykład; do klikania wybierz scenariusz 01. |
| 05 | `research-running` — Research w toku | Migawka running: worker pobiera i analizuje źródła. W demo nie pobiera internetu. Aktywne zadanie blokuje równoległe płatne zadania tego tematu. |
| 06 | `research-failed` — Research nieudany — retry | Zadanie failed pokazuje błąd i przycisk retry. Ponowienie demo przechodzi przez tę samą kolejkę bez kosztów. |
| 07 | `research-ready` — Research gotowy — Brief i Write | Fakty mają rzeczywiste ID oraz powiązane źródła. Niepewności i konflikty pozostają jawne. Generowanie wymaga ukończonego Research i faktów. |
| 08 | `write-queued` — Generowanie czeka w kolejce | Migawka queued. Brief i Write są jednym zadaniem, ale osobnymi etapami modelu; nie ma jeszcze artykułu. |
| 09 | `brief-running` — Brief — plan artykułu | Migawka building_brief. Brief wybiera kąt, odbiorcę, fakty i plan sekcji; jeszcze nie tworzy gotowego tekstu. |
| 10 | `write-failed` — Write nieudany — retry | Błąd generowania nie oznacza powstania nowej wersji. Retry ponawia zadanie; poprawne checkpointy ograniczają powtarzanie pracy. |
| 11 | `draft` — Draft — QA wymagane | Wersja została wygenerowana, ale nie ma raportu QA. Wybór wersji w sekcji QA określa dokładnie analizowany tekst. |
| 12 | `qa-queued` — QA w kolejce | Migawka pending/queued. Raport powstaje już przy enqueue i jest przypięty do konkretnego ID oraz numeru wersji. |
| 13 | `qa-running` — QA w toku | Migawka running. QA korzysta tylko ze snapshotu Research i briefu tej wersji, bez nowego researchu. |
| 14 | `qa-failed` — QA nieudane — retry | Nie ma wiarygodnego wyniku, dopóki raport nie jest completed. Retry tworzy nowe zadanie i nowy raport dla tej samej wersji. |
| 15 | `qa-clean` — QA passed — brak Auto Fix | Wynik 95, zero critical i unsupported. Wersja ready_for_approval. Auto Fix jest disabled, ponieważ nie ma problemów do poprawienia. |
| 16 | `qa-unsupported` — Auto Fix dostępny — niepoparte 47% | Niepoparte zdanie jest high unsupported_claim, wynik ograniczony do 75. Auto Fix jest dostępny dzięki auto_fixable, a nie samemu niskiemu wynikowi. |
| 17 | `qa-quote` — Niepoparty cytat — manual review | Cytat przypisany osobie bez dowodu jest critical. Wynik najwyżej 60. Nie poprawiamy go automatycznie; człowiek musi zweryfikować lub usunąć fragment. |
| 18 | `qa-date` — Sprzeczna data | Research podaje premierę 1 czerwca 2026; tekst podaje 2025. Sprzeczność critical blokuje approval. |
| 19 | `qa-number` — Nieprawidłowa cena — warunkowy Auto Fix | Tekst podaje 99 USD, Research jednoznacznie 9,99 USD. Ten incorrect_number jest auto_fixable, bo istnieje poprawna wartość i powiązany fakt. |
| 20 | `qa-uncertainty` — Pominięta niepewność | Cena Enterprise niepotwierdzona, a tekst traktuje ją jako fakt. Wymagana ręczna weryfikacja; Auto Fix nie zgaduje. |
| 21 | `qa-conflict` — Konflikt źródeł | Dwa źródła wskazują różne regiony hostingu. Tekst wybiera jedną wersję bez zastrzeżenia. Auto Fix nie rozstrzyga konfliktu. |
| 22 | `qa-editorial` — Styl, struktura, tytuł i SEO | Pokazuje powtórzenia, generyczny styl, mylący tytuł i metadata. To problemy redakcyjne możliwe do poprawienia bez nowych faktów. |
| 23 | `qa-references` — Nieprawidłowe fact/source IDs | Backend wykrywa ID spoza snapshotu i zapisuje source_mismatch. Tych relacji nie wolno wymyślać; trzeba sprawdzić materiał. |
| 24 | `qa-catalog` — Katalog wszystkich typów issue | Wszystkie 16 typów issue i 4 poziomy severity. To katalog edukacyjny, nie realistyczny wynik jednego modelu; część wymaga człowieka. |
| 25 | `qa-warnings` — Warnings nie blokują Approval | QA 95 i tylko ostrzeżenia redakcyjne. Zero critical i unsupported pozwala zatwierdzić; warning nie musi oznaczać blokady. |
| 26 | `fix-queued` — Auto Fix w kolejce | Migawka pending/queued. Zapisano wersję wejściową i listę issue. Stara wersja pozostaje bez zmian. |
| 27 | `fix-running` — Auto Fix poprawia tekst | Migawka running. Aktywne zadanie blokuje drugi Auto Fix dla tego tematu. |
| 28 | `fix-failed` — Auto Fix nieudany — retry | Zadanie failed i wyniki failed dla issue; nie utworzono częściowej wersji. Możesz ponowić zadanie. |
| 29 | `fix-skipped` — Wszystkie poprawki pominięte | Brak bezpiecznej poprawki: skipped, bez nowej wersji i bez zbędnego QA. Wymagana ręczna weryfikacja. |
| 30 | `fix-qa` — Nowa wersja — QA w kolejce | Auto Fix zakończony, v2 istnieje, ale jest draft. QA v1 nie przechodzi na v2. Automatycznie dodane QA v2 jest jeszcze pending. |
| 31 | `fix-ready` — Auto Fix zakończony — Approval | v1 QA 75 → usunięcie 47% → v2 QA 95. Sprawdź Before/After i koszt 0.00; możesz zatwierdzić konkretnie v2. |
| 32 | `fix-needs-changes` — Po poprawce nadal needs_changes | Nowe QA nadal wykrywa niepoparte twierdzenie. Pozostała jedna iteracja Auto Fix; następna nie uruchamia się samoczynnie. |
| 33 | `fix-limit` — Limit dwóch iteracji | v1 → v2 → v3, dwa zakończone Auto Fix. QA nadal nie przechodzi, status manual_review_required i zero pozostałych prób. |
| 34 | `approved` — Zatwierdzona konkretna wersja | Approved oznacza decyzję człowieka dla tej wersji. Nic nie jest publikowane automatycznie. |
| 35 | `rejected` — Wersja odrzucona | Reject zapisuje powód i zachowuje historię. Możesz ręcznie edytować tekst, tworząc nową wersję wymagającą QA. |
| 36 | `superseded` — Nowe approval zastępuje stare | v1 superseded, v2 approved. Tylko jedna wersja tematu jest aktywnie zatwierdzona; obie pozostają w historii. |
| 37 | `manual-edit` — Ręczna edycja po QA | v1 ma QA i approval; v2 jest nową ręcznie edytowaną wersją draft. QA jest wymagane ponownie, nie wolno dziedziczyć starego wyniku. |
| 38 | `qa-stale` — Stary raport — hash nie pasuje | Przykład danych legacy z nieaktualnym raportem. UI oznacza stale, blokuje Auto Fix i Approval; uruchom QA dla aktualnego tekstu. |
| 39 | `queue-retrying` — Automatyczny retry po błędzie przejściowym | Migawka retrying. Worker ponawia błąd przejściowy w ramach tego samego zadania; historia prób i last_error pozostają widoczne. Kolejny Auto Fix nie jest przez to uruchamiany. |
