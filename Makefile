.PHONY: backend-install backend-run backend-test backend-migrate worker frontend-install frontend-dev

backend-install:
	cd backend && python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt

backend-run:
	cd backend && . .venv/bin/activate && uvicorn app.main:app --reload --port 8000

backend-test:
	cd backend && . .venv/bin/activate && pytest -q

backend-migrate:
	cd backend && . .venv/bin/activate && alembic upgrade head

worker:
	cd backend && . .venv/bin/activate && celery -A app.celery_app.celery_app worker --loglevel=info

frontend-install:
	cd frontend && npm install

frontend-dev:
	cd frontend && npm run dev
