.PHONY: up down build logs ps clean dev-backend dev-frontend test help

up: 
	docker compose up --build -d
	@echo ""
	@echo "  ✓  Platform starting..."
	@echo "  →  Frontend : http://localhost"
	@echo "  →  Backend  : http://localhost:8000"
	@echo "  →  API Docs : http://localhost:8000/docs"
	@echo ""
	@echo "  Default login: use DEFAULT_ADMIN_EMAIL / DEFAULT_ADMIN_PASSWORD"
	@echo ""

down: 
	docker compose down

build: 
	docker compose build --no-cache

logs: 
	docker compose logs -f

logs-backend: 
	docker compose logs -f backend

logs-frontend: 
	docker compose logs -f frontend

ps: 
	docker compose ps

restart-backend: 
	docker compose restart backend


clean: 
	docker compose down -v --remove-orphans
	docker image prune -f

clean-data: 
	docker compose run --rm backend sh -c "rm -rf /app/data/* /app/results/*"


dev-backend: 
	@echo "Starting backend on http://localhost:8000"
	cd backend && uvicorn app.main:app --reload --port 8000

dev-frontend: 
	@echo "Starting frontend on http://localhost:3000"
	cd frontend && npm run dev

install-frontend: 
	cd frontend && npm install


help: 
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	    awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}'
