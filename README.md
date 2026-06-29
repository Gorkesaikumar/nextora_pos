# Nextora POS

Multi-tenant SaaS Point-of-Sale platform for ambitious restaurants. Built with Django 5 · DRF · PostgreSQL · Redis · Celery · HTMX · Tailwind CSS · Docker · Daphne · Nginx.

## Features List

- **Multi-Tenant SaaS**: Complete data isolation (Row-Level Security) for multiple restaurant chains.
- **Inventory Management**: Real-time stock tracking, recipe management, suppliers, purchase orders, and stock adjustments.
- **Kitchen Display System (KDS)**: Real-time ticket synchronization via WebSockets (Django Channels).
- **Point of Sale (POS)**: Fast checkout, multi-tender payments, offline-ready UUID primary keys.
- **Reporting & Analytics**: Comprehensive dashboards for sales, inventory velocity, and employee performance.
- **Billing & Subscriptions**: Integration with Razorpay/Stripe for tenant SaaS billing.
- **Secure Authentication**: Argon2 hashing, robust session management, role-based access control.

## Project Structure

```
config/        Project config: env-based settings, celery, urls, asgi.
src/
  shared/      Cross-context kernel (Clean Architecture base):
    domain/        Pure Entity / ValueObject / DomainEvent
    application/   Result, ApplicationService base
    infrastructure/ base models, structured JSON logging, health probes
    tenancy/       Row-level security and tenant resolution middleware
  contexts/    Bounded contexts (Django apps):
    identity/      Custom User and auth views
    catalog/       Products, categories, modifiers
    ordering/      POS, checkout, cart, KDS
    inventory/     Stock, suppliers, POs, recipes
    billing/       SaaS subscriptions, invoices
    marketing/     Landing pages, pricing, onboarding
deploy/        Dockerfile, nginx configs, entrypoint scripts
templates/     Django templates (HTMX + Tailwind)
```

## Environment Variable Guide

All configuration is controlled via environment variables (Twelve-Factor App). Never commit secrets to the repository. Use the provided `.env.example` as a template.

### Key Variables:
- `DJANGO_SECRET_KEY`: Must be a long, random string in production.
- `DJANGO_SETTINGS_MODULE`: Set to `config.settings.prod` in production.
- `DATABASE_URL`: PostgreSQL connection string (e.g., `postgres://user:pass@db:5432/dbname`).
- `REDIS_URL`: Primary Redis instance for cache and sessions.
- `CHANNELS_REDIS_URL`: Dedicated Redis DB for WebSockets.
- `ALLOWED_HOSTS`: Comma-separated list of valid domain names.
- `CSRF_TRUSTED_ORIGINS`: Your HTTPS domain (e.g., `https://nextora.app`).

## Installation Guide (Local Development)

1. **Clone the repository:**
   ```bash
   git clone <your-repo-url>
   cd nextora
   ```

2. **Set up environment:**
   ```bash
   cp .env.example .env
   # Edit .env and provide a dummy DJANGO_SECRET_KEY
   ```

3. **Run with Docker Compose:**
   ```bash
   docker compose up --build
   ```

4. **Initialize database:**
   ```bash
   docker compose exec web python manage.py migrate
   docker compose exec web python manage.py createsuperuser
   ```

App runs on `http://localhost:8000`

## Docker Setup Guide & Deployment (Production)

This repository includes a production-ready `docker-compose.prod.yml` and Nginx reverse proxy configuration.

### Deployment Steps:

1. Provision a Linux server (Ubuntu 22.04+ recommended) with Docker and Docker Compose installed.
2. Clone the repository to the server.
3. Create a `.env` file with **secure production secrets**.
4. Start the production stack:
   ```bash
   docker-compose -f docker-compose.prod.yml up -d --build
   ```
5. Apply migrations:
   ```bash
   docker-compose -f docker-compose.prod.yml exec web python manage.py migrate
   ```
6. Set up SSL (e.g., using Certbot/Let's Encrypt) to proxy traffic to port 80.

## API Overview

The platform includes a REST API (Django REST Framework) for external integrations and mobile POS apps.
- **Authentication**: JWT or Session-based.
- **Endpoints**: Structured by bounded context (e.g., `/api/catalog/`, `/api/ordering/`).
- **WebSockets**: The KDS uses `/ws/events` for real-time order updates.

*Note: Full OpenAPI documentation is available at `/api/docs/` when running in development mode.*
