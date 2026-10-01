# TOEIC Lab — common tasks, run from the repo root. `make help` lists them.
PY ?= ./.venv/bin/python
WEB := apps/web

.PHONY: help install seed dev-api dev-web test lint build check score anki docker-up docker-down

help: ## List available targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-12s %s\n", $$1, $$2}'

install: ## Create .venv, install backend (+dev tools) and frontend dependencies
	test -x $(PY) || python3 -m venv .venv
	$(PY) -m pip install -r server/requirements-dev.txt
	cd $(WEB) && pnpm install --frozen-lockfile

seed: ## Create/migrate the SQLite DB and load lessons, vocab, questions (idempotent)
	$(PY) scripts/seed_database.py

dev-api: ## FastAPI on http://127.0.0.1:8000 with auto-reload
	$(PY) -m uvicorn server.main:app --host 127.0.0.1 --port 8000 --reload --reload-dir server

dev-web: ## Next.js on http://localhost:3005 (proxies /api/* to BACKEND_URL)
	cd $(WEB) && pnpm dev

test: ## Backend tests (temporary DB, no network)
	$(PY) -m pytest

lint: ## Frontend type-check + ESLint
	cd $(WEB) && pnpm exec tsc --noEmit && pnpm lint

build: ## Production build of the web app
	cd $(WEB) && pnpm build

check: test lint build ## Everything that must pass before committing

score: ## Raw -> scaled score, e.g. make score L=78 R=72 T=800
	$(PY) scripts/score_calculator.py --l-raw $(or $(L),75) --r-raw $(or $(R),70) --target $(or $(T),800)

anki: ## Export the vocab notebook (database) to decks/*.csv and decks/*.apkg
	$(PY) scripts/export_anki_csv.py
	$(PY) scripts/generate_anki_deck.py

docker-up: ## Build and start the API + web containers
	docker compose up -d --build

docker-down: ## Stop the containers
	docker compose down
