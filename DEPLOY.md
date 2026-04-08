# Deploy Guide

## 1) Local Development

### Backend

```bash
make backend-install
make backend-migrate
make backend-run
```

### Worker

```bash
make worker
```

### Frontend

```bash
make frontend-install
make frontend-dev
```

## 2) Docker Compose (single host)

```bash
docker compose up -d --build
```

Services:

- `postgres` on `5432`
- `redis` on `6379`
- `backend` on `8000`
- `celery_worker` background task worker

## 3) Environment Variables

See `backend/.env.example`.

Production minimum:

- `APP_ENV=prod`
- `JWT_SECRET_KEY=<strong-random-secret>`
- `DATABASE_URL=<postgres dsn>`
- `REDIS_URL=<redis dsn>`

Recommended:

- `AUTO_CREATE_TABLES=false` (use Alembic)
- `CELERY_TASK_ALWAYS_EAGER=false` (use real worker)

## 4) Migration

```bash
cd backend
source .venv/bin/activate
alembic upgrade head
```

### Existing DB safety path (when tables already exist)

If `alembic upgrade head` fails with errors like `table ... already exists`,
do **not** drop tables directly in production. Use this safe alignment flow:

1. Backup DB first (required)
2. Align Alembic version marker:

```bash
cd backend
PYTHONPATH=. .venv/bin/alembic stamp head
```

3. Verify migration chain is now healthy:

```bash
cd backend
PYTHONPATH=. .venv/bin/alembic current
PYTHONPATH=. .venv/bin/alembic upgrade head
```

4. Run health + smoke test immediately after alignment

## 5) Smoke Test

Run after deploy:

```bash
./scripts/smoke-test.sh
```

Or with custom API endpoint:

```bash
BASE_URL="http://your-host:8000" ./scripts/smoke-test.sh
```

## 6) Health Check

```bash
curl -sS http://127.0.0.1:8000/health
```

Expected:

- top-level `code=200`
- `data.checks.database.ok=true`
- `data.checks.redis.ok=true`
