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
ALLOW_REGISTRATION=false            # do czasu izolacji danych (etap 2)
```

Pierwsze konto: `make create-user-prod EMAIL=...` (lokalnie `make create-user EMAIL=...`).
API w prod działa z `--proxy-headers`: IP klienta pochodzi z `X-Forwarded-For` reverse proxy
(`FORWARDED_ALLOW_IPS`, domyślnie `*`, bo port API jest bindowany na localhost).

Ciasteczko z `Domain=.example.com` trafia do każdej subdomeny. Na tej domenie nie powinno być
niezaufanych serwisów (np. WordPress); w takim przypadku lepiej dać panelowi osobną domenę.

## Ograniczenia etapu 1

- **Brak izolacji danych:** każdy zalogowany widzi wszystkie źródła i tematy i może zlecać płatne joby.
  Model `Workspace`/`WorkspaceMember` jest gotowy pod etap 2 (`workspace_id` na `sources`/`candidates`,
  konfiguracja WordPress per workspace, zaproszenia).
- Brak weryfikacji emaila, resetu hasła i 2FA.

## Testy

- Backend: `tests/test_auth.py`. Fixture `client` jest zalogowany (nadpisany `get_current_user`),
  `anon_client` używa prawdziwego ciasteczka.
- UI: `tests/auth-ui-check.mjs` (mockowane API). Mockowane checki używają `tests/fixtures/auth.mjs`
  (`authenticate`, `corsHeaders`). Live checki wymagają `UI_TEST_EMAIL` i `UI_TEST_PASSWORD`.
