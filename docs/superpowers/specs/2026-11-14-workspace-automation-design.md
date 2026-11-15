# Sterowanie automatyką i jobami per workspace

Data: 2026-11-14. Status: projekt do akceptacji.

## Po co

Dziś automatyka jest wspólna dla całej instancji: `FETCH_INTERVAL_MINUTES` i `CLASSIFY_BATCH_LIMIT` z `.env`,
a `pipeline:scheduled` pobiera RSS i zleca płatną klasyfikację dla **wszystkich** workspace'ów naraz
(także testowych). Nie da się z panelu zatrzymać ani anulować jobów czekających w kolejce, a `make pipeline`
nie wybiera konta. Właściciel chce, żeby nic płatnego nie działo się w tle bez jego decyzji: każdy workspace
sam steruje swoją automatyką w Ustawieniach, ma hamulec na joby, a komendy `make` działają na jednym koncie.

## Cele

- **A. Automatyka per workspace** w Ustawieniach: auto-pobieranie RSS wł./wył., interwał, auto-ocena wł./wył.,
  limit ocen na przebieg. Domyślnie wszystko wyłączone.
- **B. Hamulec**: anulowanie pojedynczego joba (czekającego, ponawianego i biegnącego – ten ostatni zatrzymuje
  się przed następnym płatnym krokiem), anulowanie wszystkich oczekujących jobów workspace'u, pauza całego
  workspace'u (worker nie bierze jego jobów, automatyka nic nie zleca) i wznowienie.
- **C. `make pipeline` per konto**: `EMAIL=` / `WORKSPACE=`, bez nich błąd przy kilku workspace'ach
  (ten sam `ConsoleWorkspaceResolver` co `seed`, `seed-demo`, `wordpress-import`).

## Poza zakresem

- Przerywanie trwającego wywołania OpenAI (proces Pythona dokańcza bieżący krok; płacimy za niego).
- Harmonogram w stylu cron (konkretne godziny, dni tygodnia) – tylko interwał.
- Zmiany budżetu z panelu (zostaje `make set-budget`).
- Automatyczne łańcuchy etapów (research/pisanie) – stages dalej nigdy nie łańcuchują się same.

## Anty-cele

- Nowy workspace, który sam z siebie wydaje pieniądze.
- Anulowanie, po którym kandydat/research/QA zostaje w stanie „running” na zawsze.
- Pauza, którą `pipeline:recover` po cichu omija.
- Utrata idempotencji/fencingu kolejki (anulowanie nie może kolidować z zapisem wyniku przez workera).

## Podejścia

Automatyka:
1. **Wybrane – ustawienia w `workspaces` + scheduler co minutę.** Scheduler co minutę woła
   `pipeline:scheduled`; komenda obsługuje tylko workspace'y z włączoną automatyką i minionym interwałem.
   `.env` zostaje tylko głównym wyłącznikiem instancji.
2. Odrzucone – wspólny interwał z `.env`, per workspace tylko wł./wył. i limit: każdy ma ten sam rytm.

Hamulec:
1. **Wybrane – status `cancelled` + pauza workspace'u sprawdzana przy przejęciu joba (`ClaimJobCommand`)**
   i w `JobRunContext::ai()` przed każdym płatnym krokiem. Jedno miejsce obejmuje zwykłe uruchomienie,
   ponowienia i `pipeline:recover`.
2. Odrzucone – usuwanie wpisów z Redisa: kolejka jest trwała w `pipeline_jobs`, `pipeline:recover`
   przywróciłby job.

## Projekt

### Dane (migracja w `Workspaces/Database/Migrations`)

Kolumny w `workspaces`:

| kolumna | typ | domyślnie | znaczenie |
|---|---|---|---|
| `auto_fetch_enabled` | bool | false | scheduler pobiera RSS tego workspace'u |
| `auto_fetch_interval_minutes` | smallint | 60 | dozwolone: 15, 30, 60, 120, 360, 720, 1440 |
| `auto_classify_enabled` | bool | false | po pobraniu zleca ocenę nowych tematów (płatne) |
| `auto_classify_batch_limit` | smallint | 20 | 1–200 ocen na przebieg |
| `last_auto_run_at` | timestamp null | null | start ostatniego przebiegu automatycznego |
| `last_auto_run_result` | jsonb null | null | `{new_candidates, enqueued, errors, budget_exceeded}` |
| `paused_at` | timestamp null | null | pauza workspace'u (null = działa) |

Istniejące workspace'y dostają wartości domyślne (automatyka wyłączona). Nowy status joba `cancelled`
w `JobStatus` (terminalny, nie należy do `active()`), oraz kolumny w `pipeline_jobs`:
`cancel_requested_at` (timestamp null) i `cancelled_by` (FK users null, `nullOnDelete`).
Status jest ograniczony `ck_pipeline_jobs_status` – nowa migracja (w `Pipeline/Database/Migrations`) usuwa
i odtwarza constraint z `cancelled`. Indeks `uq_pipeline_jobs_active_candidate` zostaje bez zmian, więc
po anulowaniu można od razu zlecić etap ponownie.

### Konfiguracja

- `AUTOMATION_ENABLED` (domyślnie `true`) – główny wyłącznik: `false` = scheduler nie robi żadnych
  przebiegów automatycznych dla nikogo (recover dalej działa).
- `FETCH_INTERVAL_MINUTES` i `CLASSIFY_BATCH_LIMIT` przestają sterować schedulerem: usunięte z
  `config/content.php`, `.env.example`, `apps/platform/.env.example` i dokumentacji. Limit dla ręcznego
  `make pipeline` bierze się z ustawień workspace'u. `ClassifyPendingController` (przycisk „oceń
  oczekujące” w panelu) jako domyślnego limitu używa `auto_classify_batch_limit` workspace'u zamiast
  `content.ingestion.classify_batch_limit`.
- `routes/console.php`: `pipeline:scheduled` co minutę (`everyMinute()->withoutOverlapping()->onOneServer()`),
  gdy `AUTOMATION_ENABLED`.

### Automatyka (A)

`ScheduledPipelineService` dzieli się na przebieg jednego workspace'u i wybór workspace'ów:

- `runDue()` (scheduler): dla każdego workspace'u z `auto_fetch_enabled`, bez `paused_at`, z
  `last_auto_run_at` null albo starszym niż interwał → `runWorkspace($id, automatic: true)`.
  Błąd jednego workspace'u logowany, pozostałe biegną dalej.
- `runWorkspace($id, $automatic)`:
  1. Pauza → automatyczny przebieg pomija workspace; ręczny kończy się błędem `workspace_paused`.
  2. Zapisuje `last_auto_run_at = now` na **starcie** (przy automatycznym), żeby awaria nie powodowała
     pętli co minutę.
  3. `IngestionService::fetchAllActive($id)` (darmowe).
  4. Ocena: przy automatycznym tylko gdy `auto_classify_enabled`; przy ręcznym zawsze (jawna decyzja
     operatora). Limit = `auto_classify_batch_limit`. Reszta jak dziś: tylko tematy bez historii oceny,
     klucz idempotencji `scheduled-classify:<id>`, stop przy 402 (budżet), pominięcie przy braku
     `OPENAI_API_KEY`.
  5. Zapisuje `last_auto_run_result` (przy automatycznym).
- `pipeline:scheduled` dostaje `--workspace=` / `--email=`:
  - z opcją: `runWorkspace(id, automatic: false)` – ignoruje wł./wył. i interwał, respektuje pauzę i budżet;
  - bez opcji: `runDue()` (tryb schedulera).
- `make pipeline` wymaga `EMAIL=`/`WORKSPACE=` (`$(WS_ARGS)`; bez nich i przy kilku workspace'ach błąd
  z listą, jak `seed`). Scheduler woła komendę bez opcji.

### Hamulec (B)

- **Anulowanie joba** `POST /api/jobs/{job}/cancel` (członek workspace'u; parametr `job` już jest
  workspace-bound):
  - `queued` / `retrying` → w transakcji z `lockForUpdate`: `status = cancelled`, `finished_at`,
    `cancelled_by`, komunikat błędu `Anulowano przez użytkownika` (kod `cancelled`); potem
    `handler->failed($job, final: true, ...)`, żeby moduł zwolnił swój stan (research/QA/Auto Fix).
  - `running` → ustawia `cancel_requested_at`; odpowiedź 202 ze stanem joba. `JobRunContext::ai()`
    sprawdza flagę (świeży odczyt z bazy) **przed** wywołaniem Pythona i przy cache-hit też, i rzuca
    `JobCancelledException`. `JobRunner` łapie ją osobno: fenced zapis `cancelled` (bez retry) +
    `handler->failed(final: true)`. Jeśli job skończy się sukcesem zanim dojdzie do kolejnego kroku,
    zostaje `succeeded` (anulowanie spóźnione – UI to pokazuje).
  - stan terminalny → 409 `job_not_cancellable`.
  - biegnącej `publish_wordpress` nie wolno zatrzymać (ma kroki AI także po zapisie wpisu, np. meta SEO):
    `409 job_not_stoppable`, flaga nie jest zapisywana; UI nie pokazuje „Anuluj” dla biegnącej publikacji.
- **Anulowanie wszystkich oczekujących** `POST /api/jobs/cancel-pending` (owner): wszystkie `queued` i
  `retrying` workspace'u jak wyżej; zwraca liczbę. Biegnących nie dotyka.
- **Pauza / wznowienie** `POST /api/workspace/pause`, `POST /api/workspace/resume` (owner):
  - `ClaimJobCommand`: job workspace'u z `paused_at` nie jest przejmowany (zostaje `queued`/`retrying`).
  - `DueJobsQuery` pomija wstrzymane workspace'y (recover ich nie dispatchuje w kółko).
  - `EnqueueService::ensureAllowed`: przy pauzie 409 `workspace_paused` dla każdego rodzaju joba (także
    demo i `publish_wordpress`) – prosty model „stop wszystko”.
  - wznowienie: `paused_at = null` i natychmiastowy `RunPipelineJob::dispatch` dla zaległych
    `queued`/`retrying` z `available_at <= now` (pozostałe obsłuży recover).
  - biegnący job w chwili pauzy dokańcza bieżący krok i kolejne (pauza nie anuluje); żeby go zatrzymać –
    „Anuluj”.

### API ustawień

- `GET /api/workspace/automation` → ustawienia, `paused_at`, `last_auto_run_at`, `last_auto_run_result`,
  `next_auto_run_at` (wyliczone; null gdy wyłączone/wstrzymane), `automation_enabled_globally`.
- `PATCH /api/workspace/automation` (owner) – `spatie/laravel-data` z walidacją: interwał z listy,
  limit 1–200, booleany. Zmiana interwału nie przesuwa `last_auto_run_at`.
- Kontrolery finalne, inwokowalne, przez serwis; trasy pod `auth:sanctum`, zgodne z `ArchitectureTest`.
- Błędy w kształcie `{"detail": ...}` (`ApiException`).

### Panel (Next.js)

- **Ustawienia** – nowa karta „Automatyka” (`components/settings/automation-card.tsx`) nad WordPressem:
  przełącznik pobierania, select interwału, przełącznik oceny z ostrzeżeniem „płatne”, pole limitu,
  „ostatni przebieg: … (nowe X, zlecone Y)”, „następny: …”, baner gdy `AUTOMATION_ENABLED=false`.
  Przycisk „Wstrzymaj workspace” / „Wznów” z opisem skutków. Niewłaściciel widzi kartę tylko do odczytu.
- **Kolejka** (`/queue`) – przycisk „Anuluj” przy jobach `queued`/`retrying`/`running` (dla running
  etykieta „Zatrzymaj po bieżącym kroku”, po kliknięciu stan „Zatrzymywanie…”); przycisk
  „Anuluj wszystkie oczekujące” (owner, z potwierdzeniem w UI, nie `window.confirm`); baner „Workspace
  wstrzymany” z przyciskiem „Wznów”.
- `types/api.ts`: `JobStatus` + `"cancelled"`, pole `cancel_requested_at`; nowy typ ustawień.
  `lib/jobs.ts`, `job-status.tsx`, `status-badge.tsx`, `agent-progress.tsx` obsługują `cancelled` jako stan
  terminalny (nie „aktywny”, nie „błąd”). Widok kandydata po anulowaniu pozwala zlecić etap ponownie.
- Enqueue przy pauzie: komunikat z `workspace_paused` z linkiem do Ustawień.

### Testy

- Laravel: per workspace interwał i wł./wył. (dwa workspace'y, różne ustawienia, `travel()` w czasie);
  pauza blokuje claim, recover i enqueue; wznowienie dispatchuje zaległe; anulowanie queued/retrying/
  running (flaga → wyjątek przed `ai()`; brak drugiego płatnego wywołania; handler.failed wołany);
  anulowanie terminalnego → 409; cancel-pending tylko własny workspace; izolacja (obce ID → 404);
  ręczny `pipeline:scheduled --email` ignoruje wyłączoną automatykę, respektuje pauzę i budżet;
  bez opcji przy kilku workspace'ach – tryb schedulera (nie błąd). Walidacja PATCH.
- Frontend: unit testy `lib/jobs` dla `cancelled`; mockowany UI check karty automatyki i anulowania
  w kolejce (wzorem `tests/*-ui-check.mjs`).

### Dokumentacja

`docs/platform/README.md` (kolejka: statusy, anulowanie, pauza, scheduler co minutę), `docs/auth/README.md`
(uprawnienia: kto co może), README i CLAUDE.md (`make pipeline EMAIL=`, `AUTOMATION_ENABLED`, usunięte
zmienne), `.env.example`.

## Decyzje właściciela

- A1 + B1 (ustawienia per workspace + scheduler co minutę; status `cancelled` + pauza przy przejęciu joba).
- `make pipeline` i reszta `make` działają per konto (`EMAIL=`/`WORKSPACE=`).

## Decyzje projektowe (do sprawdzenia)

- Nowe i istniejące workspace'y: automatyka wyłączona, domyślny interwał 60 min, limit 20.
- Wszystko robi właściciel konta (od 2026-11-15: jedno konto = jeden tenant, brak członków i ról).
- Pauza blokuje każdy rodzaj joba (także publikację WP i demo) i zlecanie nowych.
- Ręczny `make pipeline` zleca ocenę także przy wyłączonej auto-ocenie (jawna decyzja), z limitem workspace'u.
- `FETCH_INTERVAL_MINUTES`/`CLASSIFY_BATCH_LIMIT` usunięte; zostaje `AUTOMATION_ENABLED`.
- Anulowanie biegnącego joba działa na granicy kroków AI; trwający krok jest płatny.

## Dla implementującego

Nazwy klas/plików, kształt odpowiedzi JSON poza polami wymienionymi wyżej, wygląd komponentów (shadcn/ui
na `@base-ui/react`, styl istniejących kart Ustawień) i podział na commity.
