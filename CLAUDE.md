# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

AI Content Engine: RSS/Atom ingestion → LLM classification → research → article writing → QA → Auto Fix → approval → WordPress publication. Monorepo:
- `apps/platform` – Laravel 13 (PHP 8.4): the whole application except AI. Auth (Sanctum SPA), workspaces, REST API, Redis queue + worker, scheduler, RSS (SimplePie), persistence (PostgreSQL 17), HTTP to WordPress.
- `apps/ai` – Python 3.13, stateless CLI `python -m ai` (JSON on stdin → JSON on stdout). Only AI/content computation: classify, research (incl. fetching/extracting source pages), brief/write, QA, Auto Fix, SEO, WordPress HTML rendering. No DB, no HTTP server, no queue.
- `apps/web` – Next.js 16 App Router, React 19, TS strict, Tailwind 4, shadcn/ui on `@base-ui/react`. Talks only to Laravel.
- `integrations/wordpress/content-engine-bridge` – WP plugin (idempotency, conflict detection).

README, `docs/` and Python comments are written in **Polish**; UI text is Polish. Every Python file starts with a `# Rola pliku: ...` comment; keep that convention. Laravel code has **no comments** unless strictly necessary. Architecture and AI contract: `docs/platform/README.md`.

## Commands

Everything runs in Docker (`docker compose`); see `Makefile`.

```bash
make up            # db, redis, migrate, platform (:8000, artisan serve), queue, scheduler, web (:3000) – production web build
make dev           # same, but web runs `next dev` with apps/web mounted (hot reload)
make test          # test-platform (php artisan test) + test-ai (pytest in /opt/ai venv); needs running stack
make migrate       # php artisan migrate (also runs via the `migrate` service)
make seed [GROUPS=ai,php,...] / seed-demo  [EMAIL=<user>|WORKSPACE=<id>]  # RSS sources by topic group (finance opt-in) / demo topics (zero-cost)
make pipeline EMAIL=<user>|WORKSPACE=<id>  # one-off run for one workspace: fetch RSS + enqueue classification (paid)
make create-user EMAIL=... [WORKSPACE=<id>]     # interactive password; WORKSPACE joins as owner
make set-budget WORKSPACE=<id> USD=<amount|default>
make wipe          # pg_dump to /tmp, stop queue/scheduler, `artisan data:wipe` (domain tables + pipeline queue; accounts, WP connections kept)
make deactivate-user / activate-user EMAIL=...   # users.is_active; inactive users are filtered by the `active_eloquent` auth provider
make wordpress-import [EMAIL=<user>|WORKSPACE=<id>]  # WP connection from WORDPRESS_URL/USERNAME/APP_PASSWORD
make artisan CMD="route:list"
make deploy / deploy-init / logs-prod / ps-prod / migrate-prod / create-user-prod / (de)activate-user-prod / set-budget-prod / seed-prod / wordpress-import-prod
```

- Single Laravel test: `docker compose exec -T platform php artisan test --filter=ClassName` (tests in `apps/platform/tests/{Feature,Unit}`, grouped per module).
- Single Python test: `docker compose exec -T -w /srv/ai platform /opt/ai/bin/python -m pytest -q tests/test_x.py`.
- New migration: put it in `apps/platform/src/<Module>/Database/Migrations/` (loaded by `ModulesServiceProvider`).
- `apps/platform` and `apps/ai` are volume-mounted in dev. After PHP changes affecting queue/scheduler: `docker compose restart queue scheduler`. Python changes need no restart (new process per task).
- Production web image needs rebuild after frontend changes: `docker compose up -d --build web` (not under `make dev`).
- Dev Laravel config is `apps/platform/.env` (compose does **not** use `env_file`; `DB_HOST=db`, `REDIS_HOST=redis` must be in that file because `artisan serve` does not pass container env). Root `.env` holds only `NEXT_PUBLIC_API_URL` in dev; in prod it is the single config source for Laravel (`.env.example`).
- `phpunit.xml` forces `DB_DATABASE=content_test` (created by `docker/postgres/init.sql`) – tests never touch the dev DB. `RefreshDatabase` is used.
- `docker-compose.prod.yml` is standalone (never combine with `docker-compose.yml`), project `content-engine-prod`: Dockerfile target `app` (php-fpm as `www-data`, code baked in) behind `nginx`, plus `queue`, `scheduler`, `redis` (AOF), `db` (no published port), `web`. `DB_*` are built from `POSTGRES_*`. `API_BIND`/`WEB_BIND` default to `127.0.0.1` (TLS reverse proxy in front).
- `apps/platform/Dockerfile` (context `./apps`): `base` = php:8.4-fpm + Python venv `/opt/ai` with `apps/ai/requirements.txt`; `dev` adds pytest and runs `artisan serve`.

Frontend (`apps/web`):

```bash
npm run lint
npm test                 # node --test tests/*.test.mjs (pure unit tests, no network)
npm run test:ui          # Playwright check against a running build with ALL API calls mocked
npm run test:queue       # same for the queue panel
node tests/<name>-ui-check.mjs   # other mocked UI checks
```

UI checks need a running frontend (`npm run start -- --hostname 127.0.0.1 --port 3107`, or `UI_TEST_PORT=3000` for the Docker one), Playwright via `PLAYWRIGHT_MODULE=<abs path>` and optionally `CHROME_PATH`. Details in `apps/web/tests/README.md`.

**Next.js warning** (`apps/web/AGENTS.md`): this Next.js version has breaking changes vs. training data – read the relevant guide in `apps/web/node_modules/next/dist/docs/` before writing frontend code. `next dev` re-adds its block to `apps/web/AGENTS.md`; commit it rather than stripping it from diffs.

## Laravel architecture (binding conventions)

Modules in `apps/platform/src/<Module>/` (namespace `Modules\<Module>`): `Http/Controllers`, `Data`, `Services`, `Queries`, `Commands`, `Models`, `Jobs`, `Enums`, `Exceptions`, `Console` (`*Command.php` auto-registered), `Database/Migrations`. Modules: Shared, Auth, Workspaces, Usage, Sources, Candidates, Pipeline, Ai, Classification, Research, Articles, Qa, AutoFix, WordPress, Demo.

- Controllers: `final`, invokable (one action), thin; routing via `spatie/laravel-route-attributes` attributes (prefix `api`, config `config/route-attributes.php`); `auth:sanctum` on everything except register/login/logout.
- Validate everything: request input via `spatie/laravel-data` classes with validation attributes; strong typing.
- Controller → Service (plain classes, SOLID/DRY) → optionally `Queries\*Query` / `Commands\*Command`, which expose **only** `execute()` and do DB work only.
- `tests/Feature/Architecture/ArchitectureTest.php` enforces: final invokable protected controllers, single-`execute` queries/commands, every route parameter workspace-bound, foreign IDs → 404 on every route.
- Errors keep the old FastAPI shape: `{"detail": {...}}` / `{"detail": "..."}` via `Shared/Exceptions/ApiException` + `ExceptionRenderer` (422 → `detail: [{loc, msg}]`, 401 `not_authenticated`, 404 `not_found`).
- No Filament (for now).

### Auth & workspaces

Sanctum SPA: session in Redis, cookie `ce_session`, CSRF via `/sanctum/csrf-cookie` + `X-XSRF-TOKEN` (`bootstrap/app.php` `statefulApi()`, `trustProxies('*')`; CORS from `FRONTEND_URL` with credentials). Registration creates a workspace (owner). `Workspaces/Services/CurrentWorkspace` (scoped) resolves the user's workspace; `requireOwner` guards owner-only actions.

**Workspace isolation**: `workspace_id` on `sources`, `candidates`, `pipeline_jobs`, `pipeline_job_batches` (composite FKs keep candidate/source/job consistent; everything else belongs via `candidate_id`). Route params `source, candidate, article, version, fix, job` are bound only within the current workspace (`Shared/Routing/WorkspaceBindings`) – a new ID param must be added there. Lists/aggregates must filter by the current workspace explicitly. Worker/scheduler are system-wide.

**AI budget**: `Usage/BudgetService` sums call costs from `pipeline_job_attempts` for the workspace this UTC month; enqueue of new paid jobs (not `publish_wordpress`, not demo) → `402 budget_exceeded` once `workspaces.monthly_budget_usd` (or `DEFAULT_MONTHLY_BUDGET_USD`, default 10, empty = unlimited) is reached.

Tests: `Tests\TestCase::signIn()` creates a workspace + owner and acts as them; `otherWorkspace()` for isolation; `spa()` adds Origin/Referer. Frontend mocked UI checks need `authenticate(page)`, `corsHeaders(route)` and `fakeCsrf` from `apps/web/tests/fixtures/auth.mjs`.

### Durable job queue (central concept)

All paid/slow steps (`classify`, `research`, `write`, `qa_article`, `auto_fix_article`, `prepare_wordpress`, `publish_wordpress`) are rows in `pipeline_jobs`, executed by `Pipeline/Jobs/RunPipelineJob` on Redis queue `pipeline` (`queue:work`), never in the HTTP request:
- `Pipeline/Services/EnqueueService` stores input snapshot, returns `202` + job + `Location`. `Idempotency-Key` dedupes; same key with different input → `409`. At most one active AI job per candidate (collision → `409` with `code`, `job_id`). Stages never auto-chain.
- `JobRunner` claims with a lease, dispatches via `HandlerRegistry` to per-module handlers. **Fencing**: every durable write goes through `RunningJobWriter` (locks row, checks attempt token); result + `succeeded` in one transaction (`JobRunContext::finish`).
- **Checkpoints**: `JobRunContext::ai($step, $task, $input)` runs the Python task and stores `{result, calls}` under `ai:<step>`, so retries reuse finished steps instead of paying again. Crashed calls are recorded with unknown cost.
- `FailurePolicy`: retryable errors (429/5xx/timeout/connection/`ai_process_failed`) up to `JOB_MAX_ATTEMPTS`, delay ~15 s then ~60 s (respects `Retry-After`); others fail.
- Scheduler (`routes/console.php`): `pipeline:recover` every minute (lost/interrupted jobs re-dispatched); with `AUTOMATION_ENABLED` also `pipeline:scheduled` every minute, which runs only workspaces whose own automation (`workspaces.auto_*`, panel Settings → Automatyka, default off) is due and not paused.
- **Brakes**: status `cancelled` (terminal). `POST jobs/{job}/cancel` cancels queued/retrying at once and flags running jobs (`cancel_requested_at`), which stop before the next `JobRunContext::ai()` step; `POST jobs/cancel-pending` (owner). `workspaces.paused_at` (`POST workspace/pause|resume`, owner) blocks claim, recover redispatch and enqueue (`409 workspace_paused`).

### AI process

`Ai/Services/AiRunner` runs `/opt/ai/bin/python -m ai` in `/srv/ai` via `Process`, input `{"task", "demo", "input"}`; models, `LLM_PRICING` and limits are passed as env vars from `config/content.php`. Output `{"ok", "result" | "error": {code, message, retryable, retry_after}, "calls"}`. Laravel tests fake it with `Tests\Support\FakesAi` (`Process::fake`); the Demo feature test runs the real Python in demo mode.

Python side (`apps/ai`): `ai/__main__.py`, `ai/runtime.py`, task registry `ai/tasks/__init__.py`, `ai/context.py` (`TaskContext`: settings, providers, paid-call recording with cost), `ai/providers.py` (OpenAI, SDK retries disabled), `ai/demo_providers.py`. Domain logic lives in `app/services/{llm,research,article,qa,auto_fix,wordpress}` and `app/schemas` (pure, no DB). OpenAI only; provider swap = new class + `ai/providers.py`. Model changes are env-only.

**Demo mode**: candidates whose URL starts with `https://demo.content-engine.invalid/` (`Candidate::DEMO_PREFIX`) run with `demo: true` → static responses, zero cost.

### Domain flow

`Source` → `Candidate` (status `pending/approved/ignored`, scores, category) → `Research` (sources with origin original/search/manual, facts with basis/importance, fact↔source links) → `Article` (each row is a **version**; `is_current`, status) → `ArticleQa` (pass threshold `QA_PASS_SCORE`, hash-bound to the version) → `ArticleFix` (Auto Fix creates a new version; QA and approval are separate manual steps) → `WordPressPublication` (one per candidate).

WordPress connection is per workspace (`WordPress/Services/ConnectionService`; panel `/settings` via WP's authorize-application screen or manually); the app password uses the `encrypted` cast (`APP_KEY`). `WordPressClient` only reaches public IPs (pinned with `CURLOPT_RESOLVE`) unless `WORDPRESS_ALLOW_PRIVATE_URLS=true` (local Docker WP: add `-f docker-compose.wordpress.yml`, external network `goldendev-wordpress_default`). Publishing requires an approved version with a current passing QA, defaults to draft, never auto-overwrites WP, and depends on the Bridge plugin. SEO adapters: yoast / rankmath / none. See `docs/wordpress/README.md`.

## Frontend architecture

- Pages: `/login`, `/register`, `/settings` (+ `/settings/wordpress/callback`), `/` (candidates dashboard), `/candidates/[id]` (multi-stage pipeline workspace with stepper + shared sidebar), `/sources`, `/queue`.
- `lib/api.ts` is the single API client (Sanctum CSRF, `credentials: "include"`, redirect on 401); response types in `types/api.ts` (keep in sync with Laravel `Data` classes). `NEXT_PUBLIC_API_URL` is compiled into the build.
- Job polling/progress: `hooks/use-candidate-jobs.ts`, `lib/jobs.ts`, `components/agent-progress.tsx`. Unresolved idempotency keys persist in session storage.
- Pipeline/stage logic in `lib/workflow.ts`, `lib/candidate-status.ts`, `lib/article-status.ts` (covered by `tests/*.test.mjs`).

## Docs

`docs/platform/README.md` (architecture, AI contract, queue), `docs/auth/README.md` (auth, isolation, budgets), per-feature specs in `docs/{qa,auto-fix,readability,wordpress,demo,ui}/`. Queue design history: `docs/superpowers/`.
