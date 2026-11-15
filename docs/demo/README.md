# Tryb demo — cały pipeline bez kosztów AI

Tryb demo pozwala przejść wszystkie etapy (ocena, research, artykuł, QA, Auto Fix, zatwierdzenie) na fikcyjnych tematach. Nie wymaga klucza OpenAI ani internetu, a koszt i tokeny zawsze wynoszą 0.

## Jak dodać tematy demo

**Z panelu (zalecane):** **Ustawienia → Tryb demo → Utwórz tematy demo**. Gdy tematy demo już istnieją, przycisk nazywa się **Zresetuj tematy demo** i najpierw prosi o potwierdzenie.

Reset dotyczy wyłącznie tematów demo bieżącego konta (workspace'u):

1. Usuwa wszystkie tematy z adresem w przestrzeni `https://demo.content-engine.invalid/` razem z ich pracą: oceną, researchem, wersjami artykułów, raportami QA, poprawkami Auto Fix, historią zadań, publikacjami i sugestiami redakcyjnymi. Usuwa też źródło `[DEMO]`.
2. Tworzy od nowa źródło `[DEMO] Scenariusze pipeline — 0 kosztów AI` (nieaktywne, więc nie jest pobierane z RSS) i trzy tematy demo.

Prawdziwe tematy i inne konta pozostają bez zmian. Prawdziwy temat zgrupowany z tematem demo zostaje odłączony od grupy. Gdy dla tematu demo trwa zadanie (w kolejce, w toku lub czeka na ponowienie), reset zwraca `409 demo_jobs_active` — poczekaj albo anuluj zadanie w **Kolejce**. Jeśli temat demo był wysłany do WordPressa, wpis w WordPressie zostaje; usuwany jest tylko zapis publikacji w aplikacji.

API: `POST /api/demo/reset` → `201 {"removed": <liczba usuniętych tematów>, "created": 3}`.

**Z konsoli:**

```bash
make dev          # albo make up
make seed-demo EMAIL=<konto>   # albo WORKSPACE=<id>; bez parametru działa tylko przy jednym workspace
```

`make seed-demo` (`php artisan demo:seed`) **nie** resetuje: dopisuje tylko brakujące tematy i zachowuje to, co już w nich zrobiono. Do czystego startu używaj przycisku w ustawieniach.

Na liście tematów wybierz źródło `[DEMO]` w filtrze **Źródło**. Temat demo ma oznaczenie „Demo · bez kosztów AI”, a płatne przyciski dopisek „demo · bezpłatne”.

## Jak to działa

- Kliknięcia działają jak w normalnym temacie: requesty zwracają `202`, zadanie trafia do kolejki, wykonuje je worker, powstają prawdziwe rekordy i historia wersji.
- Proces AI dostaje `demo: true` i zamiast OpenAI używa lokalnych dostawców (`apps/ai/ai/demo_providers.py`) ze stałymi odpowiedziami. Zadania demo nie liczą się do miesięcznego budżetu.
- O trybie demo decyduje wyłącznie zapisany adres tematu (`Candidate::DEMO_PREFIX`). Klient nie może włączyć demo dla zwykłego tematu flagą w requeście — zwykłe tematy zawsze korzystają z prawdziwych usług i kosztują.
- W trybie demo `seo.prepare` przy publikacji nie woła modelu (profil SEO wyliczany jest z artykułu).

## Tematy demo

| Nr | Temat | Co sprawdzić |
|---|---|---|
| 01 | `discovered` — Zacznij tutaj — cały interaktywny flow | Wszystkie etapy. Pisarz demo celowo dodaje niepoparte „47%”; Auto Fix usuwa zdanie, a QA nowej wersji przechodzi. |
| 02 | `second-run` — Drugi przebieg — porównanie wersji | Ten sam flow na osobnym temacie: nowa wersja, ręczna edycja, historia wersji. |
| 03 | `ignored` — Temat pominięty | Decyzja „pomiń” nie usuwa historii; temat można przywrócić do oczekujących. |

## Przejście krok po kroku (temat 01)

Strona tematu ma 7 etapów w górnej nawigacji. Każdy etap ma po prawej panel akcji o tym samym układzie: główna akcja → akcje dodatkowe → **Następny etap** → koszt. Opis etapu otwiera **Jak działa ten etap?**, koszty — **Koszt i szczegóły uruchomienia**.

1. **Temat** — przeczytaj materiał. **Zatwierdź temat** to decyzja redakcyjna o temacie, nie zatwierdzenie artykułu.
2. **Ocena tematu** — kliknij **Oceń temat · demo · bezpłatne**. Powstanie wynik 84/100 z uzasadnieniem. Ocena jest opcjonalna.
3. **Research** — kliknij **Uruchom research**. Zobaczysz źródła, fakty z powiązaniami, niepewności i sprzeczności.
4. **Generowanie** — kliknij **Generuj artykuł** i potwierdź opcje w oknie. Jedno zadanie wykonuje brief i pisanie. Powstaje wersja 1 bez QA i bez zatwierdzenia.
5. **QA / jakość** — sprawdź, która wersja jest wybrana, i kliknij **Uruchom QA**. QA zgłosi niepoparte twierdzenie („Nexa zwiększa produktywność o 47%.”); wynik nie przekroczy 75, więc QA nie jest zaliczone. QA samo niczego nie poprawia — przejdź dalej przyciskiem **Przejdź do poprawek i zatwierdzenia**.
6. **Poprawki i zatwierdzenie** — kliknij **Popraw automatycznie**. Raport pokaże poprawione i pominięte problemy oraz zmiany „przed / po”; powstanie wersja 2 (rodzic: wersja 1), a wersja 1 zostaje bez zmian. Kliknij **Przejdź do QA wybranej wersji** i uruchom QA wersji 2 — przejdzie. Wróć do etapu 6 i kliknij **Zatwierdź wersję**. Zatwierdzenie dotyczy tylko tej wersji i niczego nie publikuje.
7. **WordPress** — przy podłączonym WordPressie możesz utworzyć szkic zatwierdzonej wersji. Bez połączenia etap pokaże, gdzie je skonfigurować.

Dodatkowo: **Edytuj tekst** i zapis tworzy kolejną wersję, która wymaga nowego QA; stary raport zostaje przy starej wersji.

## Co robi każdy etap i jakie ma warunki

| Etap | Działanie | Warunki i rezultat |
|---|---|---|
| 1. Temat | RSS zapisuje temat: tytuł, opis, adres oryginału, źródło, datę. W demo tematy tworzy reset/seeder. | Nie używa AI i nie tworzy artykułu. Zatwierdzenie tematu ≠ zatwierdzenie artykułu. |
| 2. Ocena | Trafność 40%, aktualność 20%, potencjał wyszukiwań 25%, potencjał komercyjny 15%; kategoria i uzasadnienie. | Brak innego aktywnego zadania tematu. Nie jest warunkiem researchu. |
| 3. Research | Źródła, fakty (z podstawą i ważnością), powiązania fakt↔źródło, niepewności, sprzeczności. | Ukończony research z co najmniej jednym faktem odblokowuje generowanie. Stare wersje artykułu zachowują swój snapshot dowodów. |
| 4. Generowanie | Brief (kąt, odbiorca, fakty, plan sekcji, długość), a potem tekst — w jednym zadaniu. | Każda generacja tworzy nową wersję; poprzednie zostają w historii. Nowa wersja nie ma QA ani zatwierdzenia. |
| 5. QA | Porównuje konkretną wersję ze snapshotem researchu i briefem: twierdzenia, liczby, daty, cytaty, referencje, niepewności, konflikty, styl, strukturę, SEO. | Bez internetu i nowego researchu. Raport jest przypięty do treści wersji (hash); po zmianie tekstu staje się nieaktualny. |
| 6. Poprawki i zatwierdzenie | Auto Fix: minimalne poprawki wskazanych problemów, bez nowych faktów. Zatwierdzenie/odrzucenie: decyzja człowieka o konkretnej wersji. | Auto Fix wymaga aktualnego, ukończonego QA z problemami do automatycznej poprawy i wolnej iteracji. Zatwierdzenie wymaga aktualnego, zaliczonego QA. |
| 7. WordPress | Wysyłka zatwierdzonej wersji jako szkic, wpis zaplanowany albo opublikowany, z danymi SEO. | Wymaga połączenia z WordPressem i wtyczki Bridge. Domyślnie szkic; zmian z WordPressa nie nadpisuje bez potwierdzenia. |

## QA zaliczone i Auto Fix

Wynik QA to zaokrąglona średnia ważona: fakty 40%, źródła 20%, styl 15%, struktura 15%, SEO 10%. Problem krytyczny ogranicza wynik do 60, niepoparte twierdzenie o wysokiej wadze — do 75. Próg `QA_PASS_SCORE` domyślnie 85. QA jest zaliczone, gdy:

```text
overall_score >= pass_score
critical_issue_count == 0
unsupported_claims_count == 0
```

To odblokowuje stan **gotowy do zatwierdzenia**, a nie publikację. Wynik 90 przy niepopartym twierdzeniu nadal nie zalicza QA.

Auto Fix nigdy nie uruchamia się sam. Dostępność zależy od **problemów**, nie od punktów. Obsługiwane typy: `unsupported_claim`, `title_mismatch`, `repetition`, `style_issue`, `structure_issue`, `seo_issue`, `overclaim`, `too_close_to_source`, `unverified_number`; `incorrect_number` i `incorrect_date` tylko z jednoznacznym poprawnym faktem w researchu. Flaga `auto_fixable` jest konieczna, ale backend sprawdza też typ, dowody, fragment poprawki i zakres zmian. Cytaty, sprzeczności i niebezpieczne konflikty wymagają ręcznej weryfikacji; problem może zostać pominięty, jeśli poprawka nie jest bezpieczna.

Po Auto Fix nowa wersja wymaga QA uruchomionego ręcznie. Gdy wszystkie poprawki zostaną pominięte i tekst się nie zmieni, nowa wersja nie powstaje. `AUTO_FIX_MAX_ITERATIONS` (domyślnie 2) ogranicza zakończone próby w historii wersji; techniczne ponowienie zadania nie jest osobną iteracją. Po wyczerpaniu limitu i nieudanym QA wersja wymaga ręcznej weryfikacji. Zmiana większa niż `AUTO_FIX_MAX_CHANGE_RATIO` (domyślnie 0.35) może dodać ostrzeżenie.

## Kolejka i wersje

- `queued` — czeka na workera; `running` — worker pracuje; `retrying` — automatyczne ponowienie po błędzie przejściowym; `succeeded` — wynik zapisany; `failed` — błąd końcowy, możliwe ręczne ponowienie; `cancelled` — anulowane.
- Status zadania nie jest statusem artykułu. QA i Auto Fix mają własne stany.
- Dla jednego tematu dopuszczalne jest jedno aktywne zadanie AI. Ten sam `Idempotency-Key` zwraca istniejące zadanie; inne równoległe zadanie dostaje konflikt.
- Ręczna edycja, nowa generacja i Auto Fix tworzą nową wersję. Historyczne wersje i ich raporty QA pozostają dostępne.

## Testy

- `docker compose exec -T platform php artisan test --filter=Demo` — pełny pipeline demo z prawdziwym procesem Pythona oraz reset (`DemoResetTest`).
- `apps/web/tests/account-ui-check.mjs` — przycisk tworzenia i resetu w Ustawieniach (API zamockowane).
- `apps/web/tests/demo-live-check.mjs` — przejście w przeglądarce na działającym stosie (wymaga workera i tematów demo).

Ograniczenie: dawny katalog nieruchomych „migawek” stanów (kolejka, błędy, nieaktualne QA, limity Auto Fix) nie został przeniesiony po migracji na Laravel; te stany pokrywają testy PHPUnit i zamockowane testy UI.
