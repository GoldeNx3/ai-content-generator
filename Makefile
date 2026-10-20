.PHONY: up dev down build migrate seed wipe logs test fetch classify

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

seed:
	docker compose exec api python -m app.jobs.seed $(if $(WORKSPACE),--workspace $(WORKSPACE))

wipe:
	python3 scripts/wipe.py

logs:
	docker compose logs -f

test:
	docker compose exec api pytest -q

fetch:
	curl -s -X POST http://localhost:8000/api/sources/fetch; echo

classify:
	curl -s -X POST http://localhost:8000/api/candidates/classify-pending; echo

# Konto bez publicznej rejestracji: make create-user EMAIL=jan@example.com (hasło pyta interaktywnie).
# WORKSPACE=<id> dołącza konto jako owner istniejącego workspace'u (np. „Domyślny” po migracji 0010).
.PHONY: create-user
create-user:
	@test -n "$(EMAIL)" || { echo "Podaj EMAIL=..."; exit 1; }
	docker compose exec api python -m app.jobs.create_user $(EMAIL) $(if $(WORKSPACE),--workspace $(WORKSPACE))

# Jednorazowo: dawna konfiguracja WORDPRESS_* z .env -> połączenie workspace'u (zachowuje publikacje).
.PHONY: wordpress-import-env
wordpress-import-env:
	docker compose exec api python -m app.jobs.wordpress_import_env $(if $(WORKSPACE),--workspace $(WORKSPACE))

# Budżet AI workspace'u: make set-budget WORKSPACE=<id> USD=25 (USD=default -> DEFAULT_MONTHLY_BUDGET_USD).
.PHONY: set-budget
set-budget:
	@test -n "$(WORKSPACE)" -a -n "$(USD)" || { echo "Podaj WORKSPACE=<id> USD=<kwota|default>"; exit 1; }
	docker compose exec api python -m app.jobs.set_budget --workspace $(WORKSPACE) $(if $(filter default,$(USD)),--default,--usd $(USD))

# Syntetyczne scenariusze + interaktywny pipeline bez wywołań AI.
.PHONY: seed-demo
seed-demo:
	docker compose exec -T api python -m app.jobs.seed_demo $(if $(WORKSPACE),--workspace $(WORKSPACE))

# Produkcja (docker-compose.prod.yml) - uruchamiaj NA serwerze, wewnątrz $(PROD_DIR) (lub przez deploy-init).
# Wymaga gotowego .env z produkcyjnymi wartościami. `git reset --hard` usuwa lokalne zmiany.
REPO_URL ?= git@gitlab.com:goldendev42/ai-content-app.git
BRANCH ?= main
PROD_DIR ?= /srv/content-engine
DC_PROD := docker compose -f docker-compose.prod.yml

.PHONY: deploy-init deploy build-prod up-prod down-prod restart-prod logs-prod ps-prod migrate-prod seed-prod create-user-prod wordpress-import-env-prod set-budget-prod
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
	$(DC_PROD) up -d --wait db
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
	$(DC_PROD) restart api worker scheduler web

logs-prod:
	$(DC_PROD) logs -f --tail=200

ps-prod:
	$(DC_PROD) ps

migrate-prod:
	$(DC_PROD) run --rm migrate

seed-prod:
	$(DC_PROD) exec -T api python -m app.jobs.seed $(if $(WORKSPACE),--workspace $(WORKSPACE))

create-user-prod:
	@test -n "$(EMAIL)" || { echo "Podaj EMAIL=..."; exit 1; }
	$(DC_PROD) exec api python -m app.jobs.create_user $(EMAIL) $(if $(WORKSPACE),--workspace $(WORKSPACE))

wordpress-import-env-prod:
	$(DC_PROD) exec api python -m app.jobs.wordpress_import_env $(if $(WORKSPACE),--workspace $(WORKSPACE))

set-budget-prod:
	@test -n "$(WORKSPACE)" -a -n "$(USD)" || { echo "Podaj WORKSPACE=<id> USD=<kwota|default>"; exit 1; }
	$(DC_PROD) exec api python -m app.jobs.set_budget --workspace $(WORKSPACE) $(if $(filter default,$(USD)),--default,--usd $(USD))
