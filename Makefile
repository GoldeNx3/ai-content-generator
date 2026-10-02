.PHONY: up down build migrate seed logs test fetch classify

up:
	docker compose up -d --build

down:
	docker compose down

build:
	docker compose build

migrate:
	docker compose exec api alembic upgrade head

seed:
	docker compose exec api python -m app.jobs.seed

logs:
	docker compose logs -f

test:
	docker compose exec api pytest -q

fetch:
	curl -s -X POST http://localhost:8000/api/sources/fetch; echo

classify:
	curl -s -X POST http://localhost:8000/api/candidates/classify-pending; echo
