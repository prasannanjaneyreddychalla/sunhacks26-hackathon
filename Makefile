.PHONY: setup check dev-api dev-ui up down
setup:
	python -m venv backend/.venv
	backend/.venv/bin/python -m pip install -e 'backend[dev]'
	cd frontend && npm ci
check:
	backend/.venv/bin/ruff check backend
	backend/.venv/bin/ruff format --check backend
	cd backend && .venv/bin/pytest
	cd frontend && npm run build
dev-api:
	cd backend && .venv/bin/uvicorn app.main:app --reload
dev-ui:
	cd frontend && npm run dev
up:
	docker compose up --build -d
down:
	docker compose --profile aws down
