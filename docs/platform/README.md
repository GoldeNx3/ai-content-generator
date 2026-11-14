# Platforma Laravel + silnik AI w Pythonie

## Podział odpowiedzialności

**Laravel 13 (`apps/platform`)** – cała aplikacja poza obliczeniami AI:
- auth (Sanctum SPA, standardowe hashe), workspace'y, izolacja danych, budżety AI;
- źródła RSS (pobieranie i parsowanie – SimplePie), kandydaci, statystyki;
- trwały stan pipeline'u: research, wersje artykułów, QA, Auto Fix, akceptacja, publikacje WP;
- kolejka (Redis), worker (`queue:work`) i scheduler (`schedule:work`): orkiestrują kroki i uruchamiają Pythona;
- WordPress: połączenie per workspace (autoryzacja aplikacji WP, hasło szyfrowane castem `encrypted` kluczem
  `APP_KEY`), HTTP do WP (ochrona SSRF: tylko publiczne IP, przypięte przez `CURLOPT_RESOLVE`) + Content Engine Bridge;
- REST API dla Next.js (te same ścieżki i kształty JSON co wcześniejsze API w Pythonie).

**Python (`apps/ai`)** – bezstanowe obliczenia na treści: `python -m ai`, JSON na stdin, JSON na stdout.
Brak bazy, serwera HTTP i kolejki. Python pobiera jedynie strony źródeł researchu (ekstrakcja treści) i woła
OpenAI/Tavily. Każde zadanie zwraca wynik i listę wywołań LLM z kosztem wyliczonym z cennika.

**Next.js (`apps/web`)** – rozmawia wyłącznie z Laravelem; logowanie przez Sanctum (`/sanctum/csrf-cookie`,
nagłówek `X-XSRF-TOKEN`, ponowienie po `419`).

## Zasady kodu (Laravel)

- Moduły: `src/<Moduł>/{Http/Controllers,Http/Requests,Data,Services,Queries,Commands,Models,Jobs,Enums,Exceptions,Console,Database/Migrations}`;
  namespace `Modules\<Moduł>`. `ModulesServiceProvider` ładuje migracje i komendy konsoli wszystkich modułów.
- Kontrolery `final`, invokable (jedna akcja), chude: walidacja w `Data` (`spatie/laravel-data`, atrybuty),
  logika w serwisie. Routing atrybutami (`spatie/laravel-route-attributes`, prefiks `api`); wszystkie trasy
  poza rejestracją/logowaniem/wylogowaniem mają `auth:sanctum`.
- Serwisy: zwykłe klasy, kilka metod, SOLID/DRY.
- `Queries\*Query` i `Commands\*Command` mają **wyłącznie** publiczną metodę `execute()` i robią tylko
  operacje bazodanowe (wymusza to test architektury).
- Izolacja workspace'ów: wiązania tras (`Shared/Routing/WorkspaceBindings`: `source`, `candidate`, `article`,
  `version`, `fix`, `job`) zwracają 404 dla cudzych ID; listy filtrują po `CurrentWorkspace`. Test izolacji
  sprawdza każdą trasę z ID.
- Błędy API w formacie FastAPI: `{"detail": {...}}` lub `{"detail": "..."}`; walidacja → `422` z
  `detail: [{loc, msg}]` (`Shared/Exceptions/ExceptionRenderer`).
- Testy PHPUnit (Feature + Unit) do wszystkiego; bez komentarzy w kodzie, chyba że konieczne.

## Kontrakt zadań AI (stdin → stdout)

Wejście: `{"task": "...", "demo": bool, "input": {...}}`. Modele, cennik (`LLM_PRICING`) i limity Laravel
przekazuje w zmiennych środowiskowych procesu (`AiRunner`, wartości z `config/content.php`).

Wyjście sukcesu: `{"ok": true, "result": {...}, "calls": [{"stage", "finished", "usage", "response_id", "estimated_cost_usd"}]}`.
Wyjście błędu: `{"ok": false, "error": {"code", "message", "retryable", "retry_after"}, "calls": [...]}` (kod wyjścia 0).
Brak poprawnego JSON na stdout (awaria interpretera, timeout) Laravel traktuje jako błąd ponawialny `ai_process_failed`.
Wywołanie z `finished: false` to przerwane płatne wywołanie: koszt nieznany, nie zerowy.

| Zadanie | Wejście | Wynik |
|---|---|---|
| `classify` | kandydat | oceny, kategoria, uzasadnienie, `total_score` |
| `research.extract` | lista URL + domena oryginału | dla każdego: status pobrania, tytuł, wydawca, data, treść, typ i ocena źródła |
| `research.discover` | kandydat, treść oryginału, znane URL | zapytania, nowe źródła (już pobrane i ocenione) |
| `research.analyse` | kandydat, pobrane źródła | podsumowanie, fakty z `source_ids`, niepewności, konflikty, korekty typów źródeł |
| `article.brief` | kandydat, snapshot researchu, opcje, ostatnie struktury | kontekst + brief |
| `article.write` | kontekst + brief | treść, sekcje, SEO, ostrzeżenia, statystyki |
| `article.rebuild` | wersja po ręcznej edycji | przeliczona treść, statystyki, ostrzeżenia |
| `seo.preview` | wersja | podgląd SEO |
| `qa.evaluate` | wersja artykułu + snapshot | wyniki, problemy, `qa_passed` |
| `autofix.fix` | wersja, wybrane problemy QA | nowa treść, zmiany, fixed/skipped |
| `seo.profile` / `seo.prepare` | wersja, nadpisania | pełny profil SEO (`prepare` uzupełnia braki przez LLM) |
| `wordpress.render` | wersja, profil | HTML wpisu, slug |
| `wordpress.metadata` / `wordpress.verify_meta` | profil / zapisany post, wtyczka SEO | meta wtyczki SEO / ostrzeżenia |

Każdy krok jest osobnym wywołaniem. Wynik trafia do checkpointu joba (`ai:<krok>`) przed następnym krokiem,
więc ponowienie nie płaci ponownie za ukończone kroki (np. brief).

## Kolejka

- `pipeline_jobs` (UUID, kind, status `queued/running/retrying/succeeded/failed/cancelled`, stage, próby, checkpointy,
  wynik, błąd) + `pipeline_job_attempts` (wywołania LLM z kosztami) – źródło stanu dla UI i budżetu;
  `pipeline_job_batches` – członkostwo partii `classify-pending`.
- API zapisuje job i wysyła `RunPipelineJob` do kolejki Redis `pipeline`; odpowiedź `202` + obiekt joba + `Location`.
  Jeden aktywny job AI na kandydata (kolizja → `409` z `code` i `job_id`), `Idempotency-Key` → ten sam job,
  inne wejście pod tym samym kluczem → `409`. Etapy nie łączą się automatycznie.
- `JobRunner`: claim z dzierżawą (timeout etapu + zapas), każdy trwały zapis przez `RunningJobWriter`
  (fencing: blokada wiersza i sprawdzenie tokenu próby), wynik i `succeeded` w jednej transakcji.
- Ponowienia (`FailurePolicy`): błędy `retryable` (429/5xx/timeout/połączenie/awaria procesu AI) do
  `JOB_MAX_ATTEMPTS` z opóźnieniem ~15 s, potem ~60 s (z uwzględnieniem `Retry-After`); pozostałe → `failed`.
- Anulowanie: `POST /api/jobs/{job}/cancel` – job `queued`/`retrying` od razu dostaje `cancelled` (handler etapu
  zwalnia swój stan, więc etap można zlecić ponownie); job `running` dostaje `cancel_requested_at` i zatrzymuje się
  przed kolejnym płatnym krokiem (`JobRunContext::ai()` sprawdza flagę, `JobCancelledException`). Trwające wywołanie
  AI jest dokańczane i liczone. Biegnącej `publish_wordpress` nie można zatrzymać (`409 job_not_stoppable`), bo przerwanie
  między zapisem wpisu a meta SEO zostawiłoby niekompletny wpis; czekającą w kolejce można anulować. Kod odpowiedzi: `200`
  po anulowaniu, `202` gdy job tylko oflagowano. Oflagowany job z błędem przejściowym kończy jako `cancelled`, bez
  ponowienia. Terminalny job → `409
  job_not_cancellable`. `POST /api/jobs/cancel-pending` (owner) anuluje wszystkie oczekujące joby workspace'u.
- Pauza: `POST /api/workspace/pause` / `resume` (owner) ustawia `workspaces.paused_at`. Wstrzymanego workspace'u
  nie przejmuje worker (`ClaimJobCommand`), nie wznawia `pipeline:recover`, a zlecenie nowego joba daje `409
  workspace_paused`. Wznowienie od razu oddaje zaległe joby do kolejki.
- Automatyka per workspace (`GET`/`PATCH /api/workspace/automation`, panel: Ustawienia → Automatyka): pobieranie
  RSS wł./wył. z interwałem (15 min – 24 h), ocena po pobraniu wł./wył. z limitem 1–200; domyślnie wyłączona.
- Scheduler (`routes/console.php`): `pipeline:recover` co minutę (zgubione/przerwane joby wracają do kolejki) oraz,
  przy `AUTOMATION_ENABLED=true`, `pipeline:scheduled` co minutę: obsługuje tylko workspace'y z włączoną automatyką,
  bez pauzy i z minionym interwałem; zapisuje `last_auto_run_at`/`last_auto_run_result`. Ręcznie dla jednego konta:
  `make pipeline EMAIL=<konto>` (pomija wł./wył. i interwał, respektuje pauzę i budżet).
- Budżet: `Usage/BudgetService` sumuje koszty wywołań workspace'u w bieżącym miesiącu UTC; nowe płatne joby
  (nie `publish_wordpress`, nie demo) dostają `402 budget_exceeded`.

## Uruchomienie

Dev (`make up`/`make dev`): obraz `platform/Dockerfile` target `dev` (`artisan serve`, pytest w venv `/opt/ai`),
kod `apps/platform` i `apps/ai` montowany wolumenem; konfiguracja w `apps/platform/.env`.
Po zmianach PHP w kodzie kolejki: `docker compose restart queue scheduler`.

Prod (`make deploy`, `docker-compose.prod.yml`): target `app` (php-fpm, kod wbudowany w obraz, użytkownik
`www-data`) za kontenerem `nginx`, do tego `queue`, `scheduler`, `redis` (AOF), `db`, `web`. Jedyną konfiguracją
jest root `.env` (patrz `.env.example`); `DB_*` compose składa z `POSTGRES_*`.

## Testy

- `make test-platform` – PHPUnit na bazie `content_test` (wymuszone w `phpunit.xml`). Test demo uruchamia
  prawdziwy Python w trybie demo (pełny pipeline classify → research → write → QA → Auto Fix → QA → approve, 0 USD).
- `make test-ai` – pytest modułów AI (bez bazy; LLM i HTTP podmienione fake'ami).
