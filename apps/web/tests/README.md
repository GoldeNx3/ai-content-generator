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

`auto-fix-ui-check.mjs` sprawdza kolejkę Auto Fix, nową wersję z automatycznym QA,
raport fixed/skipped i Before/After, approval konkretnej wersji, blokadę decyzji
podczas zmiany wersji, immutable manual edit oraz mobile. Wszystkie API są mockowane.

`demo-live-check.mjs` jest testem integracyjnym lokalnego, działającego API (nie mockuje requestów).
Wymaga uruchomionego workera, `make seed-demo` i osobnego Candidate z URL w namespace
`https://demo.content-engine.invalid/checks/`. Nie modyfikuje scenariuszy seedera;
wykonuje classify → research → write → QA oraz klika Auto Fix i Approval w UI.
Koszty są równe 0 dzięki dostawcom demo. Ustaw `PLAYWRIGHT_MODULE` jak w testach powyżej.
Pełny test kolejki bez przeglądarki i bez zewnętrznych klientów:
`docker compose exec -T api pytest -q tests/test_demo_runtime.py tests/test_demo_seed.py`.
