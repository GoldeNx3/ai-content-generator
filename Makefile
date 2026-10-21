.PHONY: up dev down build migrate seed seed-demo wipe logs test test-platform test-ai pipeline create-user set-budget artisan

ARTISAN := docker compose exec platform php artisan

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

# Przykładowe źródła RSS: WORKSPACE=<id> (domyślnie najstarszy workspace).
seed:
	$(ARTISAN) sources:seed $(if $(WORKSPACE),--workspace=$(WORKSPACE))

# Tematy demo: pełny pipeline bez wywołań AI i bez kosztów.
seed-demo:
	$(ARTISAN) demo:seed $(if $(WORKSPACE),--workspace=$(WORKSPACE))

wipe:
	python3 scripts/wipe.py

test: test-platform test-ai

test-platform:
	docker compose exec -T platform php artisan test

test-ai:
	docker compose exec -T -w /srv/ai platform /opt/ai/bin/python -m pytest -q

# Jednorazowo to, co robi scheduler: pobranie RSS ze wszystkich aktywnych źródeł i zlecenie oceny.
pipeline:
	$(ARTISAN) pipeline:scheduled

# Konto bez publicznej rejestracji: make create-user EMAIL=jan@example.com (hasło pyta interaktywnie).
# WORKSPACE=<id> dołącza konto jako owner istniejącego workspace'u.
create-user:
	@test -n "$(EMAIL)" || { echo "Podaj EMAIL=..."; exit 1; }
	$(ARTISAN) users:create $(EMAIL) $(if $(WORKSPACE),--workspace=$(WORKSPACE))

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

.PHONY: deploy-init deploy build-prod up-prod down-prod restart-prod logs-prod ps-prod migrate-prod seed-prod create-user-prod set-budget-prod
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

# Migracja przed restartem usług: błąd migracji zostawia działającą poprzednią wersję.
deploy:
	@test -f .env || { echo "Brak .env - skopiuj .env.example i uzupełnij."; exit 1; }
	git fetch origin $(BRANCH)
	git reset --hard origin/$(BRANCH)
	$(DC_PROD) build --pull
	$(DC_PROD) up -d --wait db redis
	$(DC_PROD) run --rm migrate
	$(DC_PROD) up -d --remove-orphans
	@echo "Deployed $(BRANCH)@$$(git rev-parse --short HEAD)"

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
	$(DC_PROD) exec -T platform php artisan sources:seed $(if $(WORKSPACE),--workspace=$(WORKSPACE))

create-user-prod:
	@test -n "$(EMAIL)" || { echo "Podaj EMAIL=..."; exit 1; }
	$(DC_PROD) exec platform php artisan users:create $(EMAIL) $(if $(WORKSPACE),--workspace=$(WORKSPACE))

set-budget-prod:
	@test -n "$(WORKSPACE)" -a -n "$(USD)" || { echo "Podaj WORKSPACE=<id> USD=<kwota|default>"; exit 1; }
	$(DC_PROD) exec platform php artisan workspaces:budget $(WORKSPACE) $(USD)
