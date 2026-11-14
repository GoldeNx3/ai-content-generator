.PHONY: up dev down build migrate seed seed-demo wipe logs test test-platform test-ai pipeline create-user deactivate-user activate-user set-budget wordpress-import artisan

ARTISAN := docker compose exec platform php artisan
# Wybór workspace'u dla seedów i importu: EMAIL=<konto> albo WORKSPACE=<id> (wymagane, gdy workspace'ów jest kilka).
WS_ARGS = $(if $(WORKSPACE),--workspace=$(WORKSPACE)) $(if $(EMAIL),--email=$(EMAIL))
SEED_ARGS = $(WS_ARGS) $(foreach g,$(subst $(comma), ,$(GROUPS)),--group=$(g))
comma := ,

up:
	docker compose up -d --build

dev:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build --renew-anon-volumes

down:
	docker compose down

build:
	docker compose build

migrate:
	docker compose run --rm migrate

logs:
	docker compose logs -f

# Przykładowe źródła RSS: EMAIL=<konto> | WORKSPACE=<id>, GROUPS=ai,php,... (domyślnie wszystkie poza finance).
seed:
	$(ARTISAN) sources:seed $(SEED_ARGS)

# Tematy demo: pełny pipeline bez wywołań AI i bez kosztów.
seed-demo:
	$(ARTISAN) demo:seed $(WS_ARGS)

# Kopia bazy do $TMPDIR (lub /tmp), zatrzymanie queue/scheduler, data:wipe, ponowny start tylko tego, co działało.
wipe:
	@set -e; umask 077; \
	running=$$(docker compose ps --status running --services); \
	echo "$$running" | grep -qx db || { echo "Kontener db nie działa. Uruchom najpierw make up lub make dev." >&2; exit 1; }; \
	echo "$$running" | grep -qx platform || { echo "Kontener platform nie działa. Uruchom najpierw make up lub make dev." >&2; exit 1; }; \
	backup="$${TMPDIR:-/tmp}/content-before-reset-$$(date +%Y%m%d-%H%M%S).sql"; \
	docker compose exec -T db pg_dump -U content -d content > "$$backup" || { rm -f "$$backup"; echo "Kopia bazy nie powiodła się, nic nie usunięto." >&2; exit 1; }; \
	echo "Kopia bazy: $$backup"; \
	stopped=$$(echo "$$running" | grep -xE 'queue|scheduler' | tr '\n' ' '); \
	trap '[ -z "$$stopped" ] || docker compose start $$stopped' EXIT; \
	[ -z "$$stopped" ] || docker compose stop $$stopped; \
	docker compose exec -T platform php artisan data:wipe --force; \
	echo "Aby zasilić źródła: make seed EMAIL=<konto>, następnie make pipeline."

test: test-platform test-ai

test-platform:
	docker compose exec -T platform php artisan test

test-ai:
	docker compose exec -T -w /srv/ai platform /opt/ai/bin/python -m pytest -q

# Jednorazowy przebieg dla jednego konta: pobranie RSS jego workspace'u i zlecenie oceny (płatne, limit z Ustawień).
# Działa też przy wyłączonej automatyce; odmawia przy wstrzymanym workspace'ie. EMAIL=<konto> albo WORKSPACE=<id>.
pipeline:
	@test -n "$(EMAIL)$(WORKSPACE)" || { echo "Podaj EMAIL=<konto> albo WORKSPACE=<id>"; exit 1; }
	$(ARTISAN) pipeline:scheduled $(WS_ARGS)

# Konto bez publicznej rejestracji: make create-user EMAIL=jan@example.com (hasło pyta interaktywnie).
# WORKSPACE=<id> dołącza konto jako owner istniejącego workspace'u.
create-user:
	@test -n "$(EMAIL)" || { echo "Podaj EMAIL=..."; exit 1; }
	$(ARTISAN) users:create $(EMAIL) $(if $(WORKSPACE),--workspace=$(WORKSPACE))

# Blokada konta (logowanie odrzucone, aktywne sesje tracą ważność) i odblokowanie: make deactivate-user EMAIL=...
deactivate-user:
	@test -n "$(EMAIL)" || { echo "Podaj EMAIL=..."; exit 1; }
	$(ARTISAN) users:deactivate $(EMAIL)

activate-user:
	@test -n "$(EMAIL)" || { echo "Podaj EMAIL=..."; exit 1; }
	$(ARTISAN) users:activate $(EMAIL)

# Połączenie WordPress z WORDPRESS_URL / WORDPRESS_USERNAME / WORDPRESS_APP_PASSWORD (EMAIL=<konto> | WORKSPACE=<id>).
wordpress-import:
	$(ARTISAN) wordpress:import-env $(WS_ARGS)

# Budżet AI workspace'u: make set-budget WORKSPACE=<id> USD=25 (USD=default -> DEFAULT_MONTHLY_BUDGET_USD).
set-budget:
	@test -n "$(WORKSPACE)" -a -n "$(USD)" || { echo "Podaj WORKSPACE=<id> USD=<kwota|default>"; exit 1; }
	$(ARTISAN) workspaces:budget $(WORKSPACE) $(USD)

# Dowolna komenda: make artisan CMD="route:list"
artisan:
	$(ARTISAN) $(CMD)

# Produkcja (docker-compose.prod.yml) - uruchamiaj NA serwerze, wewnątrz $(PROD_DIR) (lub przez deploy-init).
# Wymaga gotowego .env z produkcyjnymi wartościami. `git reset --hard` usuwa lokalne zmiany.
REPO_URL ?= git@gitlab.com:goldendev42/ai-content-app.git
BRANCH ?= main
PROD_DIR ?= /srv/content-engine
DC_PROD := docker compose -f docker-compose.prod.yml
PROD_ARTISAN := $(DC_PROD) exec -T platform php artisan
GREEN := \033[32m
RESET := \033[0m

.PHONY: deploy-init deploy build-prod up-prod down-prod restart-prod logs-prod ps-prod migrate-prod seed-prod create-user-prod deactivate-user-prod activate-user-prod set-budget-prod wordpress-import-prod
deploy-init:
	@if [ -d "$(PROD_DIR)/.git" ]; then \
		echo "$(PROD_DIR) już istnieje, pomijam clone."; \
	else \
		git clone --branch $(BRANCH) $(REPO_URL) $(PROD_DIR); \
	fi
	@if [ ! -f "$(PROD_DIR)/.env" ]; then \
		echo "Brak $(PROD_DIR)/.env - skopiuj .env.example i uzupełnij przed 'make deploy'."; \
		exit 1; \
	fi
	$(MAKE) -C $(PROD_DIR) deploy

deploy: ## Pull $(BRANCH), rebuild, migrate, restart, cache. Uruchamiaj wewnątrz $(PROD_DIR) (lub przez deploy-init).
	@test -f .env || { echo "Brak .env - skopiuj .env.example i uzupełnij."; exit 1; }
	git fetch origin $(BRANCH)
	git reset --hard origin/$(BRANCH)
	$(DC_PROD) build --pull
	$(DC_PROD) up -d --wait db redis
	# Migracja przed restartem usług: błąd migracji zostawia działającą poprzednią wersję.
	$(DC_PROD) run --rm --no-deps migrate
	$(DC_PROD) up -d --remove-orphans
	# Cache config/route/event/view po migracji: nieudana migracja nie zostawia cache z nowego kodu.
	# bootstrap/cache jest w obrazie, więc każdy długo żyjący kontener PHP buduje własny.
	$(PROD_ARTISAN) optimize
	$(DC_PROD) exec -T scheduler php artisan optimize
	@printf '$(GREEN)Deployed $(BRANCH)@%s$(RESET)\n' "$$(git rev-parse --short HEAD)"

build-prod:
	$(DC_PROD) build --pull

up-prod:
	$(DC_PROD) up -d

down-prod:
	$(DC_PROD) down

restart-prod:
	$(DC_PROD) restart platform nginx queue scheduler web

logs-prod:
	$(DC_PROD) logs -f --tail=200

ps-prod:
	$(DC_PROD) ps

migrate-prod:
	$(DC_PROD) run --rm migrate

seed-prod:
	$(DC_PROD) exec -T platform php artisan sources:seed $(SEED_ARGS)

create-user-prod:
	@test -n "$(EMAIL)" || { echo "Podaj EMAIL=..."; exit 1; }
	$(DC_PROD) exec platform php artisan users:create $(EMAIL) $(if $(WORKSPACE),--workspace=$(WORKSPACE))

set-budget-prod:
	@test -n "$(WORKSPACE)" -a -n "$(USD)" || { echo "Podaj WORKSPACE=<id> USD=<kwota|default>"; exit 1; }
	$(DC_PROD) exec platform php artisan workspaces:budget $(WORKSPACE) $(USD)

deactivate-user-prod:
	@test -n "$(EMAIL)" || { echo "Podaj EMAIL=..."; exit 1; }
	$(DC_PROD) exec -T platform php artisan users:deactivate $(EMAIL)

activate-user-prod:
	@test -n "$(EMAIL)" || { echo "Podaj EMAIL=..."; exit 1; }
	$(DC_PROD) exec -T platform php artisan users:activate $(EMAIL)

wordpress-import-prod:
	$(DC_PROD) exec -T platform php artisan wordpress:import-env $(WS_ARGS)
