.PHONY: install migrate dev bot test

# Setup
install:
	cd backend && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt

# Database migrations
migrate:
	cd backend && source venv/bin/activate && alembic upgrade head

migrate-create:
	@read -p "Migration name: " name; cd backend && source venv/bin/activate && alembic revision --autogenerate -m "$$name"

# Development
dev:
	cd backend && source venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

bot:
	cd bot && source ../backend/venv/bin/activate && python main.py

frontend:
	cd frontend && npm run dev

# Tests
test:
	cd backend && source venv/bin/activate && pytest -v

# All at once (requires tmux or separate terminals)
all:
	@echo "Use ./run.sh to start all services"
	@./run.sh
