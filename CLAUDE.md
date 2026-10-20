# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

AI Content Engine: RSS/Atom ingestion → LLM classification → research → article writing → QA → Auto Fix → approval → WordPress publication. Monorepo: `apps/api` (FastAPI, SQLAlchemy 2 async + psycopg, Alembic, Python 3.13) and `apps/web` (Next.js 16 App Router, React 19, TS strict, Tailwind 4, shadcn/ui on `@base-ui/react`). PostgreSQL 17 is both the data store and the job queue.

README, `docs/` and code comments are written in **Polish**. Every Python file starts with a `# Rola pliku: ...` comment explaining its role; keep that convention (and Polish explanatory comments) in new files.

## Commands

Everything runs in Docker (`docker compose`); see `Makefile`.

```bash
make up            # db, migrate, api (:8000, Swagger /docs), worker, scheduler, web (:3000) – production web build
make dev           # same, but web runs `next dev` with apps/web mounted (hot reload)
make migrate       # alembic upgrade head (also runs automatically via the `migrate` service)
make seed          # sample RSS sources (apps/api/app/jobs/seed.py); WORKSPACE=<id>, default = oldest workspace
make seed-demo     # synthetic pipeline scenarios using zero-cost demo providers (no AI calls)
make wipe          # backs up DB to /tmp, then truncates app data + queue (scripts/wipe.py)
make create-user EMAIL=... [WORKSPACE=<id>]   # account without public registration; WORKSPACE joins an existing one as owner (create-user-prod on server)
make test          # backend tests: docker compose exec api pytest -q (needs running stack; no Python linter configured)
make fetch / make classify
make deploy        # server only (inside PROD_DIR): git reset --hard origin/$BRANCH, build, migrate, up
make deploy-init   # first time: clone REPO_URL into PROD_DIR (default /srv/content-engine), then deploy
make logs-prod / ps-prod / migrate-prod / seed-prod / down-prod   # docker-compose.prod.yml helpers
```

`docker-compose.prod.yml` is standalone (never combine with `docker-compose.yml`), project name `content-engine-prod`: no source mounts (code baked into images), DB port not published, `DATABASE_URL` built from `POSTGRES_*` (overrides `.env`), api/web bound to `API_BIND`/`WEB_BIND` (default `127.0.0.1`, meant for a TLS reverse proxy). Requires `POSTGRES_PASSWORD` and a public `NEXT_PUBLIC_API_URL` in `.env`.

- Python code is volume-mounted; after backend changes: `docker compose restart api worker scheduler`.
- Production web image needs rebuild after frontend changes: `docker compose up -d --build web` (not needed under `make dev`).
- New migration: `docker compose exec api alembic revision --autogenerate -m "..."` (files in `apps/api/alembic/versions/`, numbered `000N_*.py`).
- Single backend test: `docker compose exec api pytest tests/test_ingestion.py -q` (add `-k name` for one test).
- Backend tests need real PostgreSQL: the session fixture in `tests/conftest.py` drops/recreates the schema of `TEST_DATABASE_URL` (`content_test`, created by `docker/postgres/init.sql`) and asserts it differs from `DATABASE_URL`. LLM/HTTP/search are faked (`FakeProvider`, `tests/*_fakes.py`, `httpx.MockTransport`); `*_live_check.py` files are manual live checks, not part of the suite.
- `scripts/tests/test_wipe.py` tests the wipe script.

Frontend (`apps/web`):

```bash
npm run lint
npm test                 # node --test tests/*.test.mjs (pure unit tests, no network)
npm run test:ui          # Playwright check against a running build with ALL API calls mocked
npm run test:queue       # same for the queue panel
node tests/<name>-ui-check.mjs   # other mocked UI checks
```

UI checks need a running frontend (`npm run start -- --hostname 127.0.0.1 --port 3107`, or `UI_TEST_PORT=3000` for the Docker one), Playwright via `PLAYWRIGHT_MODULE=<abs path>` and optionally `CHROME_PATH`. `demo-live-check.mjs` and `candidate-navigation-live-check.mjs` hit the real local API (need worker + `make seed-demo`). Details in `apps/web/tests/README.md`.

**Next.js warning** (`apps/web/AGENTS.md`): this Next.js version has breaking changes vs. training data — read the relevant guide in `apps/web/node_modules/next/dist/docs/` before writing frontend code and heed deprecation notices. `next dev` re-adds its block to `apps/web/AGENTS.md`; commit it rather than stripping it from diffs.

## Backend architecture

Layers in `apps/api/app/`:
- `api/` – thin FastAPI routers (validation, error codes), assembled in `api/router.py`.
- `services/` – business logic, independent of FastAPI (used by endpoints, worker and scheduler). Subpackages per stage: `research/`, `article/`, `qa/`, `auto_fix/`, `wordpress/`, `llm/`, `jobs/`.
- `repositories/` – SQL queries (filters, pagination, `ON CONFLICT` inserts, job claim/heartbeat).
- `models/` – ORM models; `models/__init__.py` must import every model so tables register in metadata. Enums in `models/enums.py`.
- `schemas/` – Pydantic request/response and LLM structured-output models.
- `workers/` – queue worker; `jobs/` – separate RSS scheduler process + seeders.
- `core/config.py` – `Settings` (pydantic-settings from `.env`), including model names per stage, `LLM_PRICING`, job timeouts, WordPress config.

### Auth

Session auth owned by the API (`docs/auth/README.md`): `api/auth.py` + `services/auth/`, sessions in PostgreSQL, token in HttpOnly cookie `ce_session`. Every router except `/auth` is mounted under a router with `Depends(get_current_user)` in `api/router.py`, so new routers are protected by default. An Origin-check middleware in `main.py` rejects state-changing requests from origins outside `CORS_ORIGINS`.

**Workspace isolation**: `workspace_id` on `sources`, `candidates`, `jobs`, `job_batches` (composite FKs keep candidate/source/job workspaces consistent; everything else belongs via `candidate_id`). `enforce_workspace` in `api/access.py` (router dependency) 404s any foreign ID in the path (`OWNERSHIP` maps param name → owner query; a new ID param name must be added there or `test_workspace_isolation.py` fails). Lists/aggregates must filter by `current.workspace_id` explicitly (`CurrentUserDep`); creation sets it (sources from the user, candidates from their source, jobs from their candidate). Worker/scheduler are system-wide. WordPress config is still global. Tests: fixture `client` is pre-authenticated as workspace 1, `anon_client` is not; workspaces 1 and 2 exist in every test, test data needs `workspace_id=1`. Frontend: `proxy.ts` (optimistic cookie check → `/login`), `lib/api.ts` uses `credentials: "include"` and redirects on 401. Mocked UI checks need `authenticate(page)` and `corsHeaders(route)` from `tests/fixtures/auth.mjs` (wildcard CORS fails with credentials).

### Durable job queue (central concept)

All paid/slow steps (classify, research, write, `qa_article`, `auto_fix_article`, `prepare_wordpress`, `publish_wordpress`) are **jobs in PostgreSQL**, never executed in the HTTP request:
- API enqueues via `services/jobs/service.py` with an input/model/pricing **snapshot**, returns `202` + job object + `Location`. `Idempotency-Key` header (UUID per user intent) dedupes retries; same key with different input → `409`.
- At most one active AI job per candidate across all stages (collision → `409` with `code` and `job_id`). Stages never auto-chain; each paid step is started explicitly.
- `workers/worker.py` loop: claim with `SELECT FOR UPDATE SKIP LOCKED`, lease (60 s) extended by heartbeat (10 s), dispatch through the `HANDLERS` dict (in `worker.py`) to `workers/handlers/*`. Add new job kinds there and in `workers/providers.py`.
- **Fencing**: `services/jobs/execution.py` checks lease token before every durable write (uses `session.no_autoflush`); result + `succeeded` committed in one transaction.
- **Checkpoints**: `workers/calls.py` (`CallRecorder`) records each paid LLM call and caches responses as JSON so retries reuse brief/classification/analysis instead of paying again. LLM calls are at-least-once; crashed calls are recorded as unknown cost.
- Retry policy in `services/jobs/retry.py`: 429/5xx/timeout/connection → up to 3 attempts; validation errors, refusals, `JobInputError` → fail. OpenAI SDK retries are disabled in the worker (`max_retries=0`).
- Worker writes `/tmp/worker-health.json` for the Docker healthcheck.

### LLM providers

OpenAI only, via `services/llm/` (`client.py` wrapper, one class per stage: `classify.py`, `research.py`, `write.py`, `qa.py`, `auto_fix.py`; prompts in `*_prompt.py`; cost in `cost.py`). Provider swap = new class + `services/llm/factory.py`. Model changes are `.env`-only.

**Demo mode**: candidates whose URL starts with `https://demo.content-engine.invalid/` (`app/demo.py`) are routed by the worker to `workers/demo_providers.py` (static responses, zero cost). Use this for end-to-end pipeline testing without OpenAI.

### Domain flow

`Source` → `Candidate` (status `pending/approved/ignored`, scores, category) → `Research` (sources with origin original/search/manual, facts with basis/importance, fact↔source links) → `Article` (each row is a **version**; `is_current`, `ArticleStatus`) → `ArticleQA` (scores, pass threshold `QA_PASS_SCORE`) → `ArticleFix` (Auto Fix creates a new version; QA and approval are separate manual steps) → `WordPressPublication` (one per candidate).

WordPress publishing requires an approved version with a current passing QA; defaults to draft and never auto-overwrites WP. It depends on the PHP plugin in `integrations/wordpress/content-engine-bridge/` for idempotency (instance:candidate identity, job:phase operation keys) and content-hash conflict detection. SEO adapters: yoast / rankmath / none. Local WP integration: add `-f docker-compose.wordpress.yml` (needs external network `goldendev-wordpress_default`). See `docs/wordpress/README.md`.

## Frontend architecture

- Pages: `/login`, `/register`, `/` (candidates dashboard), `/candidates/[id]` (multi-stage pipeline workspace with stepper + shared sidebar), `/sources`, `/queue`.
- `lib/api.ts` is the single API client; response types live in `types/api.ts` (keep in sync with backend schemas). `NEXT_PUBLIC_API_URL` is compiled into the build.
- Job polling/progress: `hooks/use-candidate-jobs.ts`, `lib/jobs.ts`, `components/agent-progress.tsx`. The frontend persists unresolved idempotency keys in session storage.
- Pipeline/stage logic in `lib/workflow.ts`, `lib/candidate-status.ts`, `lib/article-status.ts` (covered by `tests/*.test.mjs`).
- UI text is Polish.

## Docs

Per-feature specs and progress notes: `docs/{qa,auto-fix,readability,wordpress,demo,ui}/`. Known open backend risks (e.g. concurrent article version allocation): `docs/python-review.md`. Design/plan for the job queue: `docs/superpowers/`.
