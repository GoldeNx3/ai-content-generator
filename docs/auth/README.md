# Logowanie i konta (etap 1)

Autorytetem jest API (FastAPI). Sesje są trzymane w PostgreSQL, a przeglądarka dostaje token w ciasteczku
HttpOnly. Next.js nie ma własnej logiki uwierzytelniania.

## Przepływ

- `POST /api/auth/register` tworzy użytkownika, jego workspace (rola `owner`) i od razu sesję.
  Wymaga `ALLOW_REGISTRATION=true`.
- `POST /api/auth/login` / `POST /api/auth/logout` / `GET /api/auth/me`.
- Wszystkie inne endpointy `/api/*` wymagają sesji (`get_current_user` w `app/api/router.py`), a bez niej
  zwracają `401` z `detail.code = "not_authenticated"`. `/health` jest publiczne.
- Frontend: `proxy.ts` kieruje na `/login?next=...`, gdy brak ciasteczka (sprawdzenie optymistyczne).
  `lib/api.ts` przy `401` robi to samo. Po wylogowaniu czyszczone są klucze idempotencji w sessionStorage.

## Bezpieczeństwo

- Hasła: Argon2id (`argon2-cffi`), min. 10 znaków, rehash przy logowaniu.
- Token: 256 bitów, w bazie tylko sha256. Ciasteczko `HttpOnly; SameSite=Lax`, `Secure` w prod.
  Sesja trwa 14 dni (sliding) i jest unieważniana w bazie przy wylogowaniu.
- CSRF: POST/PUT/PATCH/DELETE z nagłówkiem `Origin` spoza `CORS_ORIGINS` dostają `403`.
- Limity (`auth_attempts`): 5 nieudanych logowań na email i 20 na IP w ciągu 15 min. Rejestracje: 5 na
  IP na godzinę, przy czym liczą się też próby z zajętym emailem. Przekroczenie daje `429` z kodem
  `too_many_attempts` (logowanie) albo `too_many_registrations` (rejestracja).
- W dev (Docker) wszystkie zapytania z hosta mają IP bramki sieci compose, więc limit per IP jest wspólny
  dla całej maszyny. W prod bez poprawnego `X-Forwarded-For` z reverse proxy wszyscy użytkownicy
  dzieliliby jedno IP, a limit rejestracji stałby się globalny. Przy `COOKIE_SECURE=true` API raz na
  proces loguje ostrzeżenie, gdy logowanie lub rejestracja przychodzi z prywatnego IP.
- Scheduler usuwa wygasłe sesje i próby starsze niż doba.

## Konfiguracja produkcyjna

```
COOKIE_DOMAIN=.example.com          # wspólne dla app.example.com i api.example.com
COOKIE_SECURE=true
CORS_ORIGINS=https://app.example.com
ALLOW_REGISTRATION=true             # koszty ogranicza DEFAULT_MONTHLY_BUDGET_USD
DEFAULT_MONTHLY_BUDGET_USD=10
```

Pierwsze konto: `make create-user-prod EMAIL=...` (lokalnie `make create-user EMAIL=...`).
API w prod działa z `--proxy-headers`: IP klienta pochodzi z `X-Forwarded-For` reverse proxy
(`FORWARDED_ALLOW_IPS`, domyślnie `*`, bo port API jest bindowany na localhost).

Ciasteczko z `Domain=.example.com` trafia do każdej subdomeny. Na tej domenie nie powinno być
niezaufanych serwisów (np. WordPress); w takim przypadku lepiej dać panelowi osobną domenę.

## Izolacja danych (etap 2)

- `workspace_id` jest na `sources`, `candidates`, `jobs` i `job_batches`. Reszta łańcucha (research,
  wersje artykułów, QA, fixy, publikacje WP) należy do workspace'u przez kandydata.
- Złożone FK w bazie: kandydat ma workspace swojego źródła, a job ma workspace swojego kandydata.
- URL źródła i kandydata jest unikalny w obrębie workspace'u. Ten sam RSS w dwóch workspace'ach daje
  osobnych kandydatów.
- **Trasy z ID:** `app/api/access.py` (`enforce_workspace`, zależność routera chronionego) sprawdza
  `candidate_id`, `source_id`, `article_id`, `version_id`, `fix_id` i `job_id` w ścieżce. Obcy albo
  nieistniejący zasób daje `404 {"code": "not_found"}`. Nowa nazwa ID w ścieżce musi trafić do `OWNERSHIP`,
  inaczej `test_every_path_parameter_is_covered_by_ownership_check` się nie powiedzie.
- **Listy i agregaty** (`/sources`, `/candidates`, `/jobs`, `/jobs/stats`, `/stats`, `classify-pending`,
  `sources/fetch`) filtrują jawnie po `current.workspace_id`. Nowa lista musi robić to samo.
- Worker i scheduler działają systemowo, ponad workspace'ami: nowi kandydaci dziedziczą workspace ze
  źródła, a joby z kandydata.
- Migracja `0010` przypisała istniejące dane do najstarszego workspace'u. Gdy były dane, a nie było kont,
  utworzyła workspace „Domyślny”. Konto dołącza się do niego przez
  `make create-user EMAIL=... WORKSPACE=<id>`. Seedy przyjmują `WORKSPACE=<id>` (domyślnie najstarszy).

## Budżet AI per workspace

- Zużycie liczone jest z zapisów płatnych wywołań w próbach jobów (`JobAttempt.llm_calls`, `CallRecorder`)
  od 1. dnia bieżącego miesiąca (UTC); liczą się też ponowienia. Wywołania przerwane przed zapisem kosztu są
  pokazywane osobno (`unknown_cost_calls`) i nie są wliczane.
- Budżet: `workspaces.monthly_budget_usd`, a gdy pusty, `DEFAULT_MONTHLY_BUDGET_USD` (puste = bez limitu).
  Ustawia go operator: `make set-budget WORKSPACE=<id> USD=25` (`USD=default` przywraca domyślny).
- Po przekroczeniu `JobService.enqueue` odrzuca nowe płatne zadania kodem `402 budget_exceeded`.
  Publikacja w WordPressie i scenariusze demo są wolne od limitu. Powtórzenie żądania z tym samym
  `Idempotency-Key` nadal zwraca istniejący job. Zadanie już zlecone może przekroczyć limit o swój koszt.
- Klasyfikacja zbiorcza zwraca `skipped_budget`. Scheduler stosuje `CLASSIFY_BATCH_LIMIT` per workspace
  i pomija workspace'y po przekroczeniu budżetu.
- Panel: Ustawienia → Zużycie AI (`GET /api/usage`).

## Ograniczenia

- WordPress jest nadal globalny (z `.env`), wspólny dla wszystkich workspace'ów.
- Wszyscy korzystają ze wspólnego klucza OpenAI; koszty ogranicza budżet workspace'u (sekcja niżej).
- Brak weryfikacji emaila, resetu hasła, 2FA, zaproszeń i przełączania workspace'ów.

## Testy

- Backend: `tests/test_auth.py`, `tests/test_workspace_isolation.py` (każda chroniona trasa z ID dla
  zasobu obcego workspace'u zwraca 404 i niczego nie zapisuje; listy, unikalności, złożone FK). Fixture `client` jest zalogowany (nadpisany `get_current_user`),
  `anon_client` używa prawdziwego ciasteczka.
- UI: `tests/auth-ui-check.mjs` (mockowane API). Mockowane checki używają `tests/fixtures/auth.mjs`
  (`authenticate`, `corsHeaders`). Live checki wymagają `UI_TEST_EMAIL` i `UI_TEST_PASSWORD`.
