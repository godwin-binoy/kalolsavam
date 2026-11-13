.PHONY: dev serve migrate seed-admin seed-stages lint audit test build check docker-up docker-down

dev:
	npm run dev

serve:
	python -m server serve

migrate:
	python -m server migrate

seed-admin:
	python -m server seed-admin

seed-stages:
	python -m server seed-stages

lint:
	ruff check server

audit:
	pip-audit -r requirements.txt

test:
	pytest -q server/tests

build:
	npm run build

check: lint test
	npx astro check

docker-up:
	docker compose up -d --build

docker-down:
	docker compose down
