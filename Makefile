.PHONY: up up-tunnel down restart logs build migrate shell ps dev clean

up:
	docker compose up -d --build

up-tunnel:
	docker compose --profile tunnel up -d --build

down:
	docker compose down

restart:
	docker compose up -d --force-recreate backend

logs:
	docker compose logs -f backend

build:
	docker compose build

migrate:
	docker compose exec backend python -m server migrate

shell:
	docker compose exec backend bash

ps:
	docker compose ps

dev:
	npm run dev

clean:
	docker compose down
