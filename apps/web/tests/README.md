# UI verification without OpenAI

`npm test` runs workflow and cost-label tests locally. No network access is needed.

For browser checks, start the built frontend with `npm run start -- --hostname 127.0.0.1 --port 3107`, then run `npm run test:ui`. The check requires Playwright and Chrome. If Playwright is available outside the project, set `PLAYWRIGHT_MODULE` to its absolute module path; `CHROME_PATH` optionally selects a Chrome executable.

The browser check intercepts **all** API requests, returns fixtures, and blocks other external requests. It never calls the real backend or OpenAI. It checks persistent fetch/batch results, queued batches, restoring research after reload, retrying a failed result read, preserving the edited article version when another generation finishes, research polling, the generation gate, the paid-generation dialog, and mobile overflow. Set `UI_TEST_PORT=3000` to verify the deployed frontend with the same mocked API. The check also verifies shared headers/footers, classification accounting, separate brief/writer accounting, and aggregate research pricing. Screenshots are saved in `/tmp/content-*.png`.


`npm run test:queue` verifies the global queue panel with intercepted API:
status counts, filters, pagination, attempts/costs, safe manual retry, automatic
updates, temporary read failures, reload and mobile width. Use the same
`PLAYWRIGHT_MODULE`, `CHROME_PATH` and `UI_TEST_PORT` settings as `test:ui`.
Queue screenshots: `/tmp/content-queue.png`, `/tmp/content-queue-mobile.png`.

QA checks cover queue/running/completed states, reload, five scores and counters,
issues, costs, retry, stale reports after editing, jumping to a collapsed section,
and mobile width. The queue fixture includes a `qa_article` job.

`auto-fix-ui-check.mjs` sprawdza kolejkę Auto Fix, nową wersję z ręcznie uruchamianym QA,
raport fixed/skipped i Before/After, approval konkretnej wersji, blokadę decyzji
podczas zmiany wersji, immutable manual edit oraz mobile. Wszystkie API są mockowane.

`demo-live-check.mjs` jest testem integracyjnym lokalnego, działającego API (nie mockuje requestów).
Wymaga uruchomionego workera, `make seed-demo` i osobnego Candidate z URL w namespace
`https://demo.content-engine.invalid/checks/`. Nie modyfikuje scenariuszy seedera;
wykonuje classify → research → write → QA oraz klika Auto Fix i Approval w UI.
Koszty są równe 0 dzięki dostawcom demo. Ustaw `PLAYWRIGHT_MODULE` jak w testach powyżej.
Pełny test kolejki bez przeglądarki i bez zewnętrznych klientów:
`docker compose exec -T api pytest -q tests/test_demo_runtime.py tests/test_demo_seed.py`.

Testy UI obejmują stale widoczny obszar „Wybrany artykuł”, wspólny wybór wersji z QA i Auto Fix, nawigację między kartami, polskie akcje, powrót do tekstu i zachowanie niezapisanej edycji po zakończeniu generowania w tle. Formularz ma powiązane etykiety, a listy i kolejka nazwane tabele.

`candidate-navigation-live-check.mjs` sprawdza rzeczywistą stronę istniejącego tematu bez zmian danych: siedem widoków, aktywną nawigację, izolację paneli, Wstecz/Dalej, historię wersji, czytanie, brak przewijania poziomego na komputerze/tablecie/telefonie oraz link pomijający nawigację. Ustaw `UI_TEST_CANDIDATE` na temat z wygenerowanym artykułem (domyślnie demo 259), `UI_TEST_PORT` i opcjonalnie `PLAYWRIGHT_MODULE`. Test wymaga gotowej aplikacji; nie uruchamia AI ani jobów.

Widok pipeline ma sześć etapów i wspólny sidebar. `candidate-navigation-live-check.mjs` sprawdza wszystkie etapy w trzech szerokościach, stepper i mobilny wybór etapu, główny wynik, sidebar, pomoc, podgląd/SEO/historię oraz Wstecz/Dalej. `auto-fix-ui-check.mjs` sprawdza przejście z QA do poprawek bez uruchomienia zadania, ręczny start Auto Fix w etapie 6 i osobne uruchomienie nowego QA. Testy nie wymagają nowych endpointów.


`candidate-actions-ui-check.mjs` sprawdza jeden przycisk researchu i wybór trybu
(analiza zachowanych źródeł / nowe wyszukiwanie), właściwe endpointy, stale
widoczne akcje z wymaganiami, czytelne pola oraz siedem etapów w szerokościach
375, 768, 1024 i 1440 px. Wszystkie API są mockowane; test nie uruchamia AI.
Przykład: `UI_TEST_PORT=3001 PLAYWRIGHT_MODULE=/ścieżka/do/playwright node tests/candidate-actions-ui-check.mjs`.
Zrzuty: `/tmp/candidate-actions-*.png`. Test Auto Fix obejmuje również przejście
zatwierdzonej wersji do WordPressa i układ formularza publikacji na telefonie.


Wspólny `AgentProgress` pokazuje fazę i czas pracy oceny, researchu, pisania,
QA i Auto Fix. Test Auto Fix sprawdza też izolację aktywności (QA nie oznacza
poprawek jako uruchomionych), przyrost sekund i zachowanie licznika po reloadzie.
Nowa wersja po naprawie czeka na ręczne uruchomienie QA; zatwierdzenie również
wymaga osobnego kliknięcia.
