.PHONY: install migrate dev bot test frontend

PYTHON=python3.11
VENV=backend/venv

install:
	cd backend && $(PYTHON) -m venv venv && ./venv/bin/pip install -r requirements.txt

migrate:
	cd backend && ./venv/bin/alembic upgrade head

migrate-create:
	@read -p "Migration name: " name; \
	cd backend && ./venv/bin/alembic revision --autogenerate -m "$$name"

dev:
	cd backend && ./venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

bot:
	cd bot && ../backend/venv/bin/python main.py

frontend:
	cd frontend && npm run dev

test:
	cd backend && ./venv/bin/pytest -v

all:
	@echo "Use ./run.sh to start all services"
	@./run.sh