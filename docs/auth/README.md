# Logowanie, workspace'y i budżety

Autorytetem jest Laravel (`apps/platform`, moduły `Auth`, `Workspaces`, `Usage`). Uwierzytelnianie to Sanctum
w trybie SPA: sesja Laravela w Redisie, ciasteczko `ce_session` (HttpOnly) i ochrona CSRF ciasteczkiem
`XSRF-TOKEN`. Next.js nie ma własnej logiki uwierzytelniania.

## Przepływ

- Panel najpierw pobiera `GET /sanctum/csrf-cookie`, potem wysyła żądania z nagłówkiem `X-XSRF-TOKEN`
  (`lib/api.ts`; po `419` odświeża token i ponawia raz). Wszystkie żądania mają `credentials: "include"`.
- `POST /api/auth/register` tworzy użytkownika, jego workspace (rola `owner`) i od razu sesję.
  Wymaga `ALLOW_REGISTRATION=true`, inaczej `403 registration_disabled`; zajęty email → `409 email_taken`.
- `POST /api/auth/login` / `POST /api/auth/logout` / `GET /api/auth/me`.
- Wszystkie inne trasy `/api/*` mają middleware `auth:sanctum`; bez sesji zwracają `401`
  z `detail.code = "not_authenticated"`. `/up` jest publiczne (healthcheck).
- Konto można zablokować (`make deactivate-user EMAIL=...`, `users.is_active = false`). Provider `active_eloquent`
  (`Auth/Providers/AuthServiceProvider.php`) pomija nieaktywnych: logowanie zwraca `401 invalid_credentials`, istniejące
  sesje dostają `401 not_authenticated`. Udane logowanie zapisuje `users.last_login_at`.
- Frontend: `proxy.ts` kieruje na `/login?next=...`, gdy brak ciasteczka (sprawdzenie optymistyczne).
  `lib/api.ts` przy `401` robi to samo. Po wylogowaniu czyszczone są klucze idempotencji w sessionStorage.

## Bezpieczeństwo

- Hasła: domyślny hasher Laravela (bcrypt), min. 10 znaków; email normalizowany (małe litery, bez spacji).
- Sesja: regenerowana przy logowaniu i rejestracji, unieważniana przy wylogowaniu; czas życia `SESSION_LIFETIME`
  (domyślnie 14 dni). W prod `SESSION_SECURE_COOKIE=true`.
- CORS i CSRF: dozwolony jest wyłącznie origin z `FRONTEND_URL` (`supports_credentials`), a sesyjne
  uwierzytelnianie dotyczy tylko domen z `SANCTUM_STATEFUL_DOMAINS`.
- Limity (`RateLimiter`): `AUTH_MAX_FAILURES_PER_EMAIL` (5) i `AUTH_MAX_FAILURES_PER_IP` (20) nieudanych
  logowań w oknie `AUTH_WINDOW_MINUTES` (15) → `429 too_many_attempts`; rejestracje
  `AUTH_MAX_REGISTRATIONS_PER_IP` (5) na `AUTH_REGISTRATION_WINDOW_MINUTES` (60) → `429 too_many_registrations`.
- IP klienta pochodzi z `X-Forwarded-For` (`trustProxies('*')`): w prod port API jest bindowany na localhost
  i dostępny tylko przez reverse proxy, które musi ustawiać ten nagłówek.

## Konfiguracja produkcyjna

```
APP_URL=https://api.example.com
FRONTEND_URL=https://app.example.com
SESSION_DOMAIN=.example.com          # wspólne dla app. i api.
SESSION_SECURE_COOKIE=true
SANCTUM_STATEFUL_DOMAINS=app.example.com
ALLOW_REGISTRATION=true              # koszty ogranicza DEFAULT_MONTHLY_BUDGET_USD
DEFAULT_MONTHLY_BUDGET_USD=10
```

Pierwsze konto: `make create-user-prod EMAIL=...` (lokalnie `make create-user EMAIL=...`), hasło pytane
interaktywnie. Ciasteczko z `Domain=.example.com` trafia do każdej subdomeny – na tej domenie nie powinno być
niezaufanych serwisów (np. WordPress); w takim przypadku panel i API powinny mieć osobną domenę.

## Izolacja danych

- `workspace_id` jest na `sources`, `candidates`, `pipeline_jobs` i `pipeline_job_batches`. Reszta łańcucha
  (research, wersje artykułów, QA, fixy, publikacje WP) należy do workspace'u przez kandydata.
- Złożone FK w bazie: kandydat ma workspace swojego źródła, a job ma workspace swojego kandydata.
- URL źródła i kandydata jest unikalny w obrębie workspace'u. Ten sam RSS w dwóch workspace'ach daje
  osobnych kandydatów.
- **Trasy z ID:** `Shared/Routing/WorkspaceBindings` wiąże parametry `source`, `candidate`, `article`,
  `version`, `fix` i `job` tylko w obrębie bieżącego workspace'u. Obcy albo nieistniejący zasób daje
  `404 {"code": "not_found"}`. Nowa trasa z ID musi używać tych nazw (test izolacji przechodzi po wszystkich trasach).
- **Listy i agregaty** filtrują jawnie po `CurrentWorkspace`. Nowa lista musi robić to samo.
- Worker i scheduler działają ponad workspace'ami: nowi kandydaci dziedziczą workspace ze źródła, a joby z kandydata.
- `make create-user EMAIL=... WORKSPACE=<id>` dołącza konto jako owner istniejącego workspace'u.
  Seedy i `wordpress-import` przyjmują `EMAIL=<konto>` albo `WORKSPACE=<id>`; bez nich działają tylko przy
  jednym workspace'ie, a przy kilku kończą się błędem z listą workspace'ów (`ConsoleWorkspaceResolver`).

## Budżet AI per workspace

- Zużycie liczone jest z zapisanych płatnych wywołań w próbach jobów (`pipeline_job_attempts`) od 1. dnia
  bieżącego miesiąca (UTC); liczą się też ponowienia. Wywołania przerwane przed zapisem kosztu są pokazywane
  osobno (`unknown_cost_calls`) i nie są wliczane.
- Budżet: `workspaces.monthly_budget_usd`, a gdy pusty, `DEFAULT_MONTHLY_BUDGET_USD` (domyślnie 10; pusta
  wartość = bez limitu). Ustawia go operator: `make set-budget WORKSPACE=<id> USD=25` (`USD=default` przywraca domyślny).
- Po przekroczeniu nowe płatne zadania dostają `402 budget_exceeded`. Publikacja w WordPressie i scenariusze
  demo są wolne od limitu. Powtórzenie żądania z tym samym `Idempotency-Key` nadal zwraca istniejący job.
  Zadanie już zlecone może przekroczyć limit o swój koszt.
- Klasyfikacja zbiorcza zwraca `skipped_budget`. Scheduler stosuje `CLASSIFY_BATCH_LIMIT` per workspace
  i pomija workspace'y po przekroczeniu budżetu.
- Panel: Ustawienia → Zużycie AI (`GET /api/usage`).

## Ograniczenia

- Wszyscy korzystają ze wspólnego klucza OpenAI; koszty ogranicza budżet workspace'u.
- Brak weryfikacji emaila, resetu hasła, 2FA, zaproszeń i przełączania workspace'ów.

## Testy

- Laravel: testy Feature modułu `Auth` (rejestracja, logowanie, limity, wylogowanie) i test izolacji
  workspace'ów (każda trasa z ID dla zasobu obcego workspace'u zwraca 404).
- UI: `apps/web/tests/auth-ui-check.mjs` (mockowane API). Mockowane checki używają `tests/fixtures/auth.mjs`
  (`authenticate`, `corsHeaders`, `fakeCsrf`). Live checki logują się przez Sanctum (`loginLive`) i wymagają
  `UI_TEST_EMAIL` i `UI_TEST_PASSWORD`.
