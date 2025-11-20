PYTHON ?= python

.PHONY: run migrate test

run:
	uvicorn main:app --host $${APP_HOST:-0.0.0.0} --port $${APP_PORT:-8000} --reload

migrate:
	ALEMBIC_CONFIG=alembic.ini alembic upgrade head

test:
	pytest -q

.PHONY: up down

up:
	docker compose up -d --build

down:
	docker compose down