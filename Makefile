.PHONY: up down build logs shell-api shell-db migrate backup

up:
	docker compose up

build:
	docker compose build

down:
	docker compose down

logs:
	docker compose logs -f

shell-api:
	docker compose exec api bash

shell-db:
	docker compose exec postgres psql -U app -d defence

migrate:
	docker compose exec api alembic upgrade head

backup:
	docker compose exec postgres pg_dump -U app defence > backup_$$(date +%Y%m%d_%H%M%S).sql
