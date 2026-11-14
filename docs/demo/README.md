# Demo pipeline bez kosztów AI

```bash
make dev       # albo make up, jeśli środowisko już jest skonfigurowane
make seed-demo # wymaga istniejącego workspace'u (zarejestruj konto w panelu)
```

Seeder (`php artisan demo:seed`) zapisuje tematy demo w tej samej bazie co aplikacja. Nie korzysta z AI, sieci ani kluczy API. `make seed` nadal dodaje normalne źródła RSS. `make seed-demo` tworzy osobne, nieaktywne źródło `[DEMO] Scenariusze pipeline — 0 kosztów AI`. Na liście tematów wybierz je w filtrze **Źródło**. Workspace wskazujesz przez `make seed-demo EMAIL=<konto>` albo `WORKSPACE=<id>`; bez tego seeder działa tylko, gdy istnieje jeden workspace.

Pracę wykonuje worker kolejki (`queue`) uruchamiający proces AI w trybie demo (`ai/demo_providers.py`). Seeder dodaje tylko brakujące tematy; kolejne uruchomienia zachowują dane i zmiany wykonane przez użytkownika. Seeder nie resetuje tematów.

## Dwa sposoby użycia

**Interaktywnie:** otwórz `[DEMO 01] Zacznij tutaj — cały interaktywny flow`. Możesz klikać normalne przyciski aplikacji. Requesty zwracają 202, pracę wykonuje worker, powstają prawdziwe rekordy i historia wersji. Dostawcy demo zwracają fikcyjne odpowiedzi lokalnie. Nie jest potrzebny klucz OpenAI. Koszty i tokeny wynoszą 0. Ochrona jest oparta na zapisanym adresie Candidate w zarezerwowanej domenie `demo.content-engine.invalid`; klient nie może włączyć demo dla zwykłego tematu przez flagę requestu. Zwykłe tematy nadal korzystają z rzeczywistych usług i mogą kosztować.

**Drugi przebieg:** temat 02 pozwala powtórzyć flow niezależnie (regeneracja, ręczna edycja, historia wersji), a temat 03 pokazuje decyzję ignored.

## Przejście krok po kroku

1. Otwórz scenariusz 01 i kliknij **Oceń temat**. Powstanie zadanie classify oraz ocena tematu. Możesz zatwierdzić temat, ale nie jest to approval artykułu.
2. Kliknij **Uruchom research**. Po workerze zobaczysz źródła, fakty, ich powiązania, niepewności i konflikty.
3. Kliknij **Generuj artykuł** i potwierdź opcje. Jedno zadanie wykonuje Brief, potem Write. Powstaje v1, bez QA i bez approval.
4. W karcie QA sprawdź **wybraną wersję** i kliknij **Run QA**. Demo Writer celowo dodaje „Nexa zwiększa produktywność o 47%.”, którego nie ma w Research. QA zgłosi high unsupported_claim; wynik nie przekroczy 75.
5. W panelu QA pojawi się **Napraw automatycznie 1 problem**. Kliknij go; ekran przejdzie do **Poprawek i zatwierdzenia**: wynik zapisze poprawione/pominięte issue, powstanie v2 z parent=v1, a QA v2 uruchamiasz osobnym kliknięciem w etapie QA. Przycisk „Otwórz nową wersję” pozwala ją wybrać. v1 pozostaje bez zmian.
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
| 7. Auto Fix | Minimalne poprawki wybranych problemów; bez nowych faktów, własnej wiedzy i researchu. | Najnowsze ukończone i aktualne QA, issue auto-fixable, pozostała iteracja, wolna kolejka. Nowa wersja + wyniki fixed/skipped zapisują się spójnie, QA tej wersji wymaga osobnego kliknięcia. |
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

Po Auto Fix nowa wersja wymaga QA; uruchom je ręcznie. Gdy wszystkie poprawki są skipped i tekst się nie zmienił, nie powstaje zbędna nowa wersja ani QA. `AUTO_FIX_MAX_ITERATIONS` domyślnie 2 ogranicza zakończone próby w historii tej gałęzi; techniczne retry zadania nie jest osobną zakończoną iteracją. Po nieudanym QA i wyczerpaniu limitu: manual_review_required. Kolejny Auto Fix wymaga kliknięcia, nie ma nieskończonej pętli. Zmiana ponad `AUTO_FIX_MAX_CHANGE_RATIO` (domyślnie 0.35) może zapisać warning; poważne poprawki struktury nie są przez to automatycznie blokowane.

## Kolejka i wersje

- `queued`: zapisane, czeka na workera; `running`: worker pracuje; `retrying`: automatyczne ponowienie po błędzie przejściowym; `succeeded`: rezultat zapisany; `failed`: błąd końcowy, możliwy ręczny retry.
- Status zadania nie jest statusem artykułu. QA i Fix mają własne pending/running/completed/failed.
- Dla jednego Candidate dopuszczone jest jedno aktywne zadanie. Duplikat z tym samym Idempotency-Key zwraca istniejące zadanie; drugi niezależny request może otrzymać konflikt.
- QA jest przypięte do ID wersji i zamrożonego wejścia. Hash niepasujący do tekstu oznacza stale i blokuje użycie starego raportu do fix/approval.
- Manual edit, regenerowanie i Auto Fix tworzą nową wersję. Historyczne wersje i QA pozostają dostępne. Nowa treść wymaga nowego QA.

## Tematy demo

| Nr | Temat | Co sprawdzić |
|---|---|---|
| 01 | `discovered` — Zacznij tutaj — cały interaktywny flow | Ocena, Research, generowanie, QA, Auto Fix i Approval. Writer celowo dodaje niepoparte 47%; Auto Fix usuwa zdanie, a nowe QA przechodzi. |
| 02 | `second-run` — Drugi przebieg — porównanie wersji | Ten sam flow na osobnym temacie: regeneracja, ręczna edycja i historia wersji. |
| 03 | `ignored` — Temat pominięty | Decyzja ignored nie usuwa historii; temat można przywrócić do oczekujących. |

Ograniczenie po migracji na Laravel: dawny katalog nieruchomych migawek stanów (kolejka, błędy, stale QA, limity
Auto Fix itd.) nie został przeniesiony; część tych stanów pokrywają testy PHPUnit. W trybie demo `seo.prepare` nie woła LLM
(zwraca profil wyliczony z artykułu).
