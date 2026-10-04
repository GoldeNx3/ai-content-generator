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
	docker compose exec api python -m app.jobs.seed

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
