# ===========================================================================
# Developer task runner. Thin wrappers over the real tools — no hidden magic.
# ===========================================================================
.DEFAULT_GOAL := help
COMPOSE := docker compose

.PHONY: help
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

.PHONY: up
up: ## Start the full dev stack
	$(COMPOSE) up --build

.PHONY: down
down: ## Stop the stack
	$(COMPOSE) down

.PHONY: migrate
migrate: ## Run database migrations
	$(COMPOSE) run --rm web python manage.py migrate

.PHONY: makemigrations
makemigrations: ## Generate migrations
	$(COMPOSE) run --rm web python manage.py makemigrations

.PHONY: superuser
superuser: ## Create a superuser
	$(COMPOSE) run --rm web python manage.py createsuperuser

.PHONY: seed
seed: ## Seed demo data (dev only)
	$(COMPOSE) run --rm web python manage.py seed_demo

.PHONY: shell
shell: ## Django shell
	$(COMPOSE) run --rm web python manage.py shell

.PHONY: test
test: ## Run the test suite
	$(COMPOSE) run --rm web pytest

.PHONY: lint
lint: ## Lint + format check
	$(COMPOSE) run --rm web ruff check .

.PHONY: typecheck
typecheck: ## Static type check
	$(COMPOSE) run --rm web mypy src

.PHONY: audit
audit: ## Dependency vulnerability scan
	$(COMPOSE) run --rm web pip-audit

.PHONY: prod
prod: ## Run the production-shaped stack (no dev override)
	$(COMPOSE) -f docker-compose.yml up --build
