# Sterowanie automatyką i jobami per workspace – plan implementacji

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Każdy workspace sam steruje automatycznym pobieraniem RSS i płatną oceną, może wstrzymać wszystkie swoje joby i anulować pojedyncze/oczekujące, a `make pipeline` działa na jednym koncie.

**Architecture:** Ustawienia i pauza jako kolumny `workspaces`; scheduler co minutę woła `pipeline:scheduled`, który obsługuje workspace'y z minionym interwałem. Hamulec wpięty w jedyne miejsce przejęcia joba (`ClaimJobCommand`), w `DueJobsQuery` (recover), w `EnqueueService` i w `JobRunContext::ai()` (granica kroków AI). Nowy terminalny status `cancelled`.

**Tech Stack:** Laravel 13 / PHP 8.4, PostgreSQL 17, spatie/laravel-data, spatie/laravel-route-attributes, Next.js 16 + React 19 + shadcn/ui na `@base-ui/react`.

**Spec:** `docs/superpowers/specs/2026-11-14-workspace-automation-design.md`

## Global Constraints

- Branch `feat/workspace-automation`; dokumenty spec/plan **nie są commitowane** (decyzja właściciela).
- Kontrolery: `final`, inwokowalne, cienkie, `#[Middleware('auth:sanctum')]`, trasy atrybutami; Query/Command wyłącznie `execute()` (wymusza `tests/Feature/Architecture/ArchitectureTest.php`).
- Kod Laravela bez komentarzy; Python nie jest zmieniany; teksty UI po polsku.
- Błędy przez `ApiException` → `{"detail": {...}}`; nowe kody: `workspace_paused` (409), `job_not_cancellable` (409); `owner_required` (403) już istnieje.
- Interwały dozwolone: `15, 30, 60, 120, 360, 720, 1440`; limit ocen `1–200`; domyślnie: automatyka wyłączona, interwał `60`, limit `20`.
- `AUTOMATION_ENABLED` (domyślnie `true`) – jedyny globalny przełącznik; `FETCH_INTERVAL_MINUTES` i `CLASSIFY_BATCH_LIMIT` znikają.
- Testy: `docker compose exec -T platform php artisan test --filter=<Klasa>`; całość `make test-platform`; frontend `cd apps/web && npm run lint && npx tsc --noEmit && npm test`.
- Commity: Conventional Commits (`feat(platform): …`, `feat(web): …`) zakończone liniami atrybucji z system-remindera.

## Review Focus

1. **Wyścig anulowania z sukcesem** – job `running` kończy `finish()` w chwili kliknięcia „Anuluj”: ma zostać `succeeded`, a flaga nie może zmienić statusu terminalnego. → test w Task 3 `cancel_request_after_success_does_not_override_result`.
2. **Pauza w trakcie ponowienia** – job `retrying` zaplanowany przez `RunPipelineJob::dispatch()->delay()` budzi się przy pauzie: nie może być przejęty ani oznaczony jako błąd. → test w Task 2 `paused_workspace_jobs_are_not_claimed`.
3. **Anulowany etap da się zlecić ponownie** – po `cancelled` research/QA nie zostają w stanie `running`, a nowy enqueue nie dostaje 409 `candidate_busy`. → test w Task 3 `cancelled_research_can_be_enqueued_again`.
4. **Zmiana interwału / włączenie po długiej przerwie** – `last_auto_run_at` sprzed tygodnia nie może wywołać serii przebiegów; jeden przebieg i licznik od nowa. → test w Task 5 `due_workspace_runs_once_per_interval`.
5. **Ręczny `make pipeline` bez opcji przy kilku workspace'ach** – scheduler woła tę komendę bez opcji, więc tryb bez opcji to `runDue()`, nie błąd; błąd daje tylko `make pipeline` (Makefile wymaga EMAIL/WORKSPACE). → test w Task 5 `command_without_options_runs_due_workspaces_only` + `make -n pipeline` w kroku weryfikacji.

---

### Task 1: Schemat, status `cancelled`, konfiguracja

**Files:**
- Create: `apps/platform/src/Workspaces/Database/Migrations/2026_11_14_000001_add_automation_to_workspaces.php`
- Create: `apps/platform/src/Pipeline/Database/Migrations/2026_11_14_000002_add_cancellation_to_pipeline_jobs.php`
- Modify: `apps/platform/src/Workspaces/Models/Workspace.php`, `apps/platform/src/Pipeline/Models/PipelineJob.php`, `apps/platform/src/Pipeline/Enums/JobStatus.php`, `apps/platform/src/Pipeline/Data/QueueFiltersData.php:14`, `apps/platform/config/content.php:22-25`
- Test: `apps/platform/tests/Feature/Pipeline/JobCancellationTest.php` (nowy; tu pierwszy test schematu)

**Interfaces:**
- Produces: kolumny `workspaces.{auto_fetch_enabled bool=false, auto_fetch_interval_minutes smallint=60, auto_classify_enabled bool=false, auto_classify_batch_limit smallint=20, last_auto_run_at timestamp null, last_auto_run_result jsonb null, paused_at timestamp null}`; `pipeline_jobs.{cancel_requested_at timestamp null, cancelled_by bigint null FK users nullOnDelete}`; `JobStatus::Cancelled = 'cancelled'` (nie w `active()`); casty `Workspace`: booleany, `last_auto_run_at`/`paused_at` → `immutable_datetime`, `last_auto_run_result` → `array`; `PipelineJob`: `cancel_requested_at` → `immutable_datetime`, oba pola w `Fillable`; `config('content.automation.enabled')` (bool, env `AUTOMATION_ENABLED`, domyślnie true). Usunięte klucze `content.ingestion.fetch_interval_minutes` i `content.ingestion.classify_batch_limit`.

- [ ] **Step 1: Test** `cancelled_status_is_accepted_by_database`: utwórz job przez `BuildsDomain`, `forceFill(['status' => JobStatus::Cancelled])->save()`, `assertSame(JobStatus::Cancelled, $job->fresh()->status)`; oraz `assertFalse(JobStatus::Cancelled->isActive())`.
- [ ] **Step 2: Uruchom** `--filter=JobCancellationTest` → FAIL (brak case `Cancelled`).
- [ ] **Step 3: Migracje.** Pipeline: `DROP CONSTRAINT ck_pipeline_jobs_status` i odtworzenie z `'cancelled'`; `down()` odwraca (najpierw `UPDATE ... SET status='failed' WHERE status='cancelled'`). Workspaces: kolumny jak wyżej. Enum, casty, `QueueFiltersData` `#[In]` + `'cancelled'`, config.
- [ ] **Step 4: Uruchom** `make migrate` i `--filter=JobCancellationTest` → PASS; `grep -rn "fetch_interval_minutes\|classify_batch_limit" apps/platform` pokazuje tylko `routes/console.php` i dwa miejsca naprawiane w Task 5 (`ScheduledPipelineService`, `ClassifyPendingController`) – na razie podmień je tymczasowo na `20`, żeby suita przechodziła.
- [ ] **Step 5: Commit** `feat(platform): schema for workspace automation and job cancellation`.

### Task 2: Pauza workspace'u

**Files:**
- Create: `apps/platform/src/Workspaces/Services/WorkspacePauseService.php`, `apps/platform/src/Workspaces/Commands/SetWorkspacePausedCommand.php`, `apps/platform/src/Workspaces/Queries/WorkspacePausedQuery.php`, `apps/platform/src/Workspaces/Http/Controllers/PauseWorkspaceController.php`, `apps/platform/src/Workspaces/Http/Controllers/ResumeWorkspaceController.php`, `apps/platform/src/Pipeline/Queries/ResumableJobsQuery.php`
- Modify: `apps/platform/src/Pipeline/Commands/ClaimJobCommand.php:17-20`, `apps/platform/src/Pipeline/Queries/DueJobsQuery.php`, `apps/platform/src/Pipeline/Services/EnqueueService.php:88-99` (routing skanuje całe `src/**/*Controller.php`, rejestracja niepotrzebna)
- Test: `apps/platform/tests/Feature/Workspaces/WorkspacePauseTest.php`

**Interfaces:**
- Consumes: `workspaces.paused_at` (Task 1).
- Produces: `WorkspacePausedQuery::execute(int $workspaceId): bool`; `SetWorkspacePausedCommand::execute(int $workspaceId, ?CarbonImmutable $pausedAt): void`; `ResumableJobsQuery::execute(int $workspaceId): Collection<PipelineJob>` (queued/retrying, `available_at <= now`); `WorkspacePauseService::pause(int $workspaceId): void`, `::resume(int $workspaceId): int` (liczba wznowionych); `POST /api/workspace/pause` → 200 `{"paused_at": "<iso>"}`, `POST /api/workspace/resume` → 200 `{"paused_at": null, "resumed_jobs": n}`; oba `requireOwner()`; `ApiException('workspace_paused', 409)` z `EnqueueService::ensureAllowed()` przed sprawdzeniem demo.

- [ ] **Step 1: Testy**
  - `paused_workspace_jobs_are_not_claimed`: job `queued` i job `retrying` z `available_at` w przeszłości; `pause`; `app(JobRunner::class)->run($id)` dla obu → statusy bez zmian, `attempt_count` 0 / bez zmian, `fakeAi` nie wywołany (`Process::assertNothingRan()`).
  - `recover_skips_paused_workspaces`: `Queue::fake()`; job queued sprzed 10 min; pauza; `artisan('pipeline:recover')` → `Queue::assertNotPushed(RunPipelineJob::class)`.
  - `enqueue_is_rejected_while_paused`: pauza → `postJson('/api/candidates/{id}/classify')` = 409 i `detail.code = workspace_paused` (także dla kandydata demo).
  - `resume_dispatches_waiting_jobs`: `Queue::fake()`; 2 joby queued; pauza, resume → odpowiedź `resumed_jobs = 2`, `Queue::assertPushed(RunPipelineJob::class, 2)`.
  - `only_owner_can_pause`: `signIn(WorkspaceRole::Member)` → 403 `owner_required`; obcy workspace nie dotknięty.
- [ ] **Step 2: Uruchom** `--filter=WorkspacePauseTest` → FAIL (404 tras).
- [ ] **Step 3: Implementacja.** `ClaimJobCommand`: `->whereNotExists(fn ($q) => $q->from('workspaces')->whereColumn('workspaces.id', 'pipeline_jobs.workspace_id')->whereNotNull('paused_at'))`. `DueJobsQuery` to samo. `EnqueueService::ensureAllowed`: pierwsza linia – pauza → wyjątek. `resume`: zapis `paused_at = null`, potem `RunPipelineJob::dispatch($job->id, $job->kind->value)` dla `ResumableJobsQuery`.
- [ ] **Step 4: Uruchom** `--filter='WorkspacePauseTest|ArchitectureTest|ClassificationPipelineTest'` → PASS.
- [ ] **Step 5: Commit** `feat(platform): pause and resume all jobs of a workspace`.

### Task 3: Anulowanie jobów

**Files:**
- Create: `apps/platform/src/Pipeline/Services/JobCancellationService.php`, `apps/platform/src/Pipeline/Commands/CancelJobCommand.php`, `apps/platform/src/Pipeline/Commands/RequestJobCancelCommand.php`, `apps/platform/src/Pipeline/Queries/PendingJobsQuery.php`, `apps/platform/src/Pipeline/Exceptions/JobCancelledException.php`, `apps/platform/src/Pipeline/Http/Controllers/CancelJobController.php`, `apps/platform/src/Pipeline/Http/Controllers/CancelPendingJobsController.php`
- Modify: `apps/platform/src/Pipeline/Services/JobRunContext.php:38-54`, `apps/platform/src/Pipeline/Services/JobRunner.php:43-53`, `apps/platform/src/Pipeline/Data/JobData.php` (+ `?CarbonImmutable $cancel_requested_at`), `apps/platform/src/Pipeline/Support/ErrorMessages.php` (kod `cancelled` → „Anulowano przez użytkownika.”)
- Test: `apps/platform/tests/Feature/Pipeline/JobCancellationTest.php`

**Interfaces:**
- Consumes: `JobStatus::Cancelled`, `pipeline_jobs.cancel_requested_at/cancelled_by` (Task 1); `HandlerRegistry::for(JobKind)->failed(PipelineJob, bool $final, string $message, ?array $details)`.
- Produces: `CancelJobCommand::execute(PipelineJob $locked, ?PipelineJobAttempt $attempt, ?int $userId): void` (status `cancelled`, `error_code='cancelled'`, `error_message`, `finished_at`, `lease_expires_at=null`, attempt `outcome='cancelled'`); `RequestJobCancelCommand::execute(PipelineJob $locked, ?int $userId): void` (tylko `cancel_requested_at`, `cancelled_by`); `PendingJobsQuery::execute(int $workspaceId): Collection` (queued/retrying, `lockForUpdate` wewnątrz transakcji serwisu); `JobCancellationService::cancel(PipelineJob $job, ?int $userId): PipelineJob`, `::cancelPending(int $workspaceId, ?int $userId): int`; `JobCancelledException` (RuntimeException); `POST /api/jobs/{job}/cancel` → 200 z `JobData` (każdy członek), `POST /api/jobs/cancel-pending` → 200 `{"cancelled": n}` (owner).
- Logika `cancel()` w transakcji z `lockForUpdate`: queued/retrying → `CancelJobCommand` + `handler->failed($locked, true, $message, null)`; running → `RequestJobCancelCommand`; terminalny → `ApiException('job_not_cancellable', 409)`.
- `JobRunContext::ai()`: przed zwróceniem cache'u i przed wywołaniem Pythona: `PipelineJob::query()->whereKey($this->job->id)->value('cancel_requested_at') !== null` → `throw new JobCancelledException`. `JobRunner::run()`: osobny `catch (JobCancelledException)` → `$this->update->fenced($job, fn ($locked, $attempt) => CancelJobCommand + handler->failed(..., true, ...))`, bez retry i bez dispatchu.

- [ ] **Step 1: Testy**
  - `queued_job_is_cancelled_immediately`: POST cancel → 200, `status=cancelled`, `error.code=cancelled`; `cancelled_by = user`.
  - `running_job_stops_before_next_paid_step`: research job w `running` z checkpointem pierwszego kroku AI; ustaw `cancel_requested_at`; uruchom handler przez `JobRunner::run` po ręcznym ustawieniu statusu `queued` (claim) → status `cancelled`, `Process` wywołany **0** razy dla kolejnego kroku (`fakeAi` + asercja liczby wywołań), research `failed`.
  - `cancel_request_after_success_does_not_override_result`: job `succeeded` → POST cancel → 409 `job_not_cancellable`; job `running`, flaga, potem `finish()` bez dalszych `ai()` → `succeeded`.
  - `cancelled_research_can_be_enqueued_again`: anuluj queued research → `postJson('/api/candidates/{id}/research')` = 202.
  - `cancel_pending_only_touches_own_queued_jobs`: 2 queued + 1 running w swoim, 1 queued w obcym → `{"cancelled": 2}`; running bez zmian (status i `cancel_requested_at = null`); obcy bez zmian; member → 403.
  - `foreign_job_cannot_be_cancelled`: job obcego workspace'u → 404.
- [ ] **Step 2: Uruchom** `--filter=JobCancellationTest` → FAIL.
- [ ] **Step 3: Implementacja** wg Interfaces.
- [ ] **Step 4: Uruchom** `--filter='JobCancellationTest|ArchitectureTest'` i `make test-platform` → PASS.
- [ ] **Step 5: Commit** `feat(platform): cancel queued, retrying and running jobs`.

### Task 4: API ustawień automatyki

**Files:**
- Create: `apps/platform/src/Workspaces/Data/AutomationSettingsData.php`, `apps/platform/src/Workspaces/Data/UpdateAutomationData.php`, `apps/platform/src/Workspaces/Services/AutomationSettingsService.php`, `apps/platform/src/Workspaces/Queries/AutomationSettingsQuery.php`, `apps/platform/src/Workspaces/Commands/UpdateAutomationCommand.php`, `apps/platform/src/Workspaces/Http/Controllers/ShowAutomationController.php`, `apps/platform/src/Workspaces/Http/Controllers/UpdateAutomationController.php`
- Test: `apps/platform/tests/Feature/Workspaces/AutomationSettingsTest.php`

**Interfaces:**
- Consumes: kolumny z Task 1.
- Produces: `AutomationSettingsData { bool auto_fetch_enabled; int auto_fetch_interval_minutes; bool auto_classify_enabled; int auto_classify_batch_limit; ?CarbonImmutable last_auto_run_at; ?array last_auto_run_result; ?CarbonImmutable next_auto_run_at; ?CarbonImmutable paused_at; bool automation_enabled_globally; bool can_edit }`; `next_auto_run_at` = null gdy `!auto_fetch_enabled` albo pauza albo `!automation_enabled_globally`, w przeciwnym razie `last_auto_run_at + interwał` albo `now` gdy null. `UpdateAutomationData` – wszystkie 4 pola opcjonalne (`Optional`), `#[In([15,30,60,120,360,720,1440])]`, `#[Between(1, 200)]`, `#[BooleanType]`. `AutomationSettingsService::show(int $workspaceId, bool $canEdit): AutomationSettingsData`, `::update(int $workspaceId, UpdateAutomationData $data): AutomationSettingsData`. Trasy: `GET /api/workspace/automation` (każdy członek), `PATCH /api/workspace/automation` (owner).

- [ ] **Step 1: Testy** `defaults_are_off` (GET → `auto_fetch_enabled=false`, `interval=60`, `limit=20`, `next_auto_run_at=null`, `can_edit=true`); `owner_updates_and_next_run_is_computed` (PATCH włącz + 30 → `next_auto_run_at` ≈ now); `invalid_values_are_rejected` (interval 45 → 422 `detail[0].loc` zawiera `auto_fetch_interval_minutes`; limit 0 i 201 → 422); `member_reads_but_cannot_update` (GET 200 `can_edit=false`, PATCH 403); `global_switch_is_reported` (`config(['content.automation.enabled' => false])` → `automation_enabled_globally=false`, `next_auto_run_at=null`).
- [ ] **Step 2: Uruchom** `--filter=AutomationSettingsTest` → FAIL.
- [ ] **Step 3: Implementacja.**
- [ ] **Step 4: Uruchom** `--filter='AutomationSettingsTest|ArchitectureTest'` → PASS.
- [ ] **Step 5: Commit** `feat(platform): per-workspace automation settings API`.

### Task 5: Scheduler per workspace i `make pipeline` per konto

**Files:**
- Create: `apps/platform/src/Classification/Queries/DueAutomationWorkspacesQuery.php`, `apps/platform/src/Workspaces/Commands/RecordAutomationRunCommand.php`
- Modify: `apps/platform/src/Classification/Services/ScheduledPipelineService.php`, `apps/platform/src/Classification/Console/RunScheduledPipelineCommand.php`, `apps/platform/src/Classification/Http/Controllers/ClassifyPendingController.php:25`, `apps/platform/routes/console.php`, `Makefile` (target `pipeline`, komentarz), `.env.example`, `apps/platform/.env.example`, `docker-compose.prod.yml` (jeśli przekazuje stare zmienne)
- Delete: `apps/platform/src/Classification/Queries/WorkspacesWithPendingClassificationQuery.php` (jeśli nieużywane po zmianie)
- Test: `apps/platform/tests/Feature/Pipeline/ScheduledPipelineTest.php` (przepisany)

**Interfaces:**
- Consumes: `ConsoleWorkspaceResolver::resolve(?string $workspace, ?string $email): int` (istnieje), `WorkspacePausedQuery` (Task 2), kolumny Task 1, `IngestionService::fetchAllActive(?int $workspaceId): FetchResultData`.
- Produces: `DueAutomationWorkspacesQuery::execute(CarbonImmutable $now): array<int>` (enabled, bez pauzy, `last_auto_run_at` null lub `<= now - interval`); `RecordAutomationRunCommand::execute(int $workspaceId, CarbonImmutable $startedAt, ?array $result): void`; `ScheduledPipelineService::runDue(): array{workspaces: int, new_candidates: int, enqueued: int}`, `::runWorkspace(int $workspaceId, bool $automatic): array{new_candidates: int, enqueued: int, errors: int, budget_exceeded: bool}`; ręczny przebieg przy pauzie → `ApiException('workspace_paused', 409)`. `pipeline:scheduled {--workspace=} {--email=}`: bez opcji → `runDue()` (gdy `content.automation.enabled`; inaczej info i SUCCESS); z opcją → `runWorkspace(..., false)`. `routes/console.php`: `if (config('content.automation.enabled')) Schedule::command('pipeline:scheduled')->everyMinute()->withoutOverlapping()->onOneServer();`. Makefile: `pipeline:` → `$(ARTISAN) pipeline:scheduled $(WS_ARGS)` z guardem `@test -n "$(EMAIL)$(WORKSPACE)" || { echo "Podaj EMAIL=<konto> albo WORKSPACE=<id>"; exit 1; }`.
- `runWorkspace`: przy automatycznym `RecordAutomationRunCommand` ze startem **przed** fetch (wynik null), po zakończeniu z wynikiem; ocena – automatycznie tylko przy `auto_classify_enabled`, ręcznie zawsze; limit `auto_classify_batch_limit`; reszta logiki klasyfikacji jak dziś (idempotencja, 402 → `budget_exceeded = true`, brak klucza → 0).

- [ ] **Step 1: Testy** (zastępują obecne)
  - `disabled_workspaces_are_not_touched`: źródło, automatyka off → `artisan('pipeline:scheduled')` → 0 kandydatów, 0 jobów.
  - `due_workspace_runs_once_per_interval`: on, 30 min, `last_auto_run_at` = tydzień temu → jeden przebieg (kandydaci + `last_auto_run_result.new_candidates = 2`); ponowne wywołanie → brak nowego przebiegu (`last_auto_run_at` bez zmian); `travel(31)->minutes()` → kolejny.
  - `classification_only_when_enabled_and_limited`: fetch on, classify off → 0 jobów; classify on + limit 1 → 1 job.
  - `paused_workspace_is_skipped_and_manual_run_fails`: pauza → scheduler nic; `artisan('pipeline:scheduled', ['--email' => ...])` → FAILED z „wstrzymany”.
  - `manual_run_ignores_disabled_automation`: automatyka off, `--workspace=<id>` → kandydaci + joby oceny (limit z ustawień); `last_auto_run_at` dalej null.
  - `command_without_options_runs_due_workspaces_only`: dwa workspace'y, tylko jeden enabled → kandydaci tylko w nim, komenda SUCCESS.
  - `budget_and_missing_key_still_respected`: przeniesione z obecnych testów (`monthly_budget_usd = 0` → 0 jobów, `budget_exceeded = true`; pusty klucz → 0 jobów).
  - `global_switch_off_runs_nothing`: `content.automation.enabled=false` → bez opcji nic się nie dzieje.
- [ ] **Step 2: Uruchom** `--filter=ScheduledPipelineTest` → FAIL.
- [ ] **Step 3: Implementacja** + Makefile, `.env.example` (usuń `FETCH_INTERVAL_MINUTES`, `CLASSIFY_BATCH_LIMIT`, dodaj `AUTOMATION_ENABLED=true` z komentarzem), `ClassifyPendingController` domyślny limit z `workspaces.auto_classify_batch_limit`.
- [ ] **Step 4: Uruchom** `make test-platform` → PASS; `make -n pipeline` → komunikat guarda i exit 1; `make -n pipeline EMAIL=a@b.pl` → `php artisan pipeline:scheduled --email=a@b.pl`; `docker compose exec -T platform php artisan schedule:list` → `pipeline:scheduled` co minutę.
- [ ] **Step 5: Commit** `feat(platform): per-workspace automation schedule and per-account make pipeline`.

### Task 6: Panel – ustawienia i kolejka

**Files:**
- Create: `apps/web/components/settings/automation-card.tsx`, `apps/web/tests/automation-ui-check.mjs`
- Modify: `apps/web/types/api.ts` (`JobStatus` + `"cancelled"`, `Job.cancel_requested_at: string | null`, typ `AutomationSettings`), `apps/web/lib/api.ts` (`automation`, `updateAutomation`, `pauseWorkspace`, `resumeWorkspace`, `cancelJob`, `cancelPendingJobs`; `ERROR_MESSAGES.workspace_paused`, `job_not_cancellable`), `apps/web/lib/jobs.ts` (`STATUS_LABELS.cancelled = "Anulowano"`, styl szary), `apps/web/components/job-status.tsx` (etykieta i ikona dla `cancelled`, nie „Błąd”), `apps/web/components/queue/job-details.tsx`, `apps/web/app/queue/page.tsx`, `apps/web/app/settings/page.tsx`, `apps/web/tests/queue-ui-check.mjs`, `apps/web/tests/job-progress.test.mjs`

**Interfaces:**
- Consumes: API z Task 2–4 (kształty jak w ich Interfaces).
- Produces: `api.automation(): Promise<AutomationSettings>`, `api.updateAutomation(body: Partial<Pick<AutomationSettings, "auto_fetch_enabled" | "auto_fetch_interval_minutes" | "auto_classify_enabled" | "auto_classify_batch_limit">>)`, `api.pauseWorkspace(): Promise<{paused_at: string}>`, `api.resumeWorkspace(): Promise<{paused_at: null; resumed_jobs: number}>`, `api.cancelJob(id: string): Promise<Job>`, `api.cancelPendingJobs(): Promise<{cancelled: number}>`.
- UI (wg spec, sekcja „Panel”): karta „Automatyka” nad WordPressem; select interwału z etykietami „co 15 min … raz na dobę”; przy auto-ocenie dopisek „płatne (OpenAI)”; „Ostatni przebieg: data · nowe X · zlecone Y”; „Następny: data” albo „wyłączone”; baner gdy `!automation_enabled_globally`; przycisk Wstrzymaj/Wznów z opisem; tylko-odczyt gdy `!can_edit`. Kolejka: „Anuluj” przy queued/retrying, „Zatrzymaj po bieżącym kroku” przy running (poza `publish_wordpress`), po kliknięciu przy running etykieta „Zatrzymywanie…” dopóki `cancel_requested_at` i status `running`; „Anuluj wszystkie oczekujące” z potwierdzeniem w UI (drugi klik „Potwierdź anulowanie N jobów”, nie `window.confirm`); baner pauzy z „Wznów” (stan z `api.automation()`).

- [ ] **Step 1: Testy**
  - `tests/job-progress.test.mjs`: `isActiveJob({status: "cancelled"})` = false; `STATUS_LABELS.cancelled` = „Anulowano”.
  - `tests/queue-ui-check.mjs`: mock joba queued → klik „Anuluj” → żądanie `POST /jobs/<id>/cancel`, wiersz pokazuje „Anulowano”; mock running → „Zatrzymaj po bieżącym kroku” → „Zatrzymywanie…”; baner pauzy przy `paused_at` → „Wznów” wysyła `POST /workspace/resume`.
  - `tests/automation-ui-check.mjs`: mock GET automation (defaults) → przełącznik pobierania → PATCH z `{"auto_fetch_enabled": true}`; select 30 → PATCH `{"auto_fetch_interval_minutes": 30}`; `can_edit=false` → kontrolki `disabled`.
- [ ] **Step 2: Uruchom** `npm test` → FAIL (brak `cancelled`).
- [ ] **Step 3: Implementacja** (przed kodem przeczytaj właściwe przewodniki w `apps/web/node_modules/next/dist/docs/`; komponenty jak `usage-card.tsx` i `wordpress-connection.tsx`).
- [ ] **Step 4: Uruchom** `npm run lint && npx tsc --noEmit && npm test`, build `npm run build`, start `npm run start -- --hostname 127.0.0.1 --port 3107`, potem `npm run test:queue` i `node tests/automation-ui-check.mjs` (z `PLAYWRIGHT_MODULE`) → PASS.
- [ ] **Step 5: Commit** `feat(web): automation settings, workspace pause and job cancellation`.

### Task 7: Dokumentacja i weryfikacja końcowa

**Files:**
- Modify: `docs/platform/README.md` (statusy z `cancelled`, anulowanie na granicy kroków, pauza, scheduler co minutę, `AUTOMATION_ENABLED`), `docs/auth/README.md` (uprawnienia: owner – ustawienia/pauza/anuluj wszystkie; członek – anuluj job), `README.md` i `CLAUDE.md` (`make pipeline EMAIL=…`, usunięte zmienne), `apps/web/tests/README.md` (nowy check)

- [ ] **Step 1:** Aktualizacja dokumentów.
- [ ] **Step 2:** `make test` → PASS; frontend jak w Task 6 Step 4 → PASS; `docker compose up -d --build web && docker compose restart queue scheduler`, ręcznie: Ustawienia → włącz pobieranie 15 min, kolejka → anuluj job demo, pauza → próba zlecenia daje komunikat `workspace_paused`.
- [ ] **Step 3: Commit** `docs: workspace automation, pause and job cancellation`.
