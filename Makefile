PYTHON ?= python

.PHONY: run migrate test

run:
	uvicorn main:app --host $${APP_HOST:-0.0.0.0} --port $${APP_PORT:-8000} --reload

migrate:
	alembic upgrade head

test:
	pytest -q