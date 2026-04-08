# Release Checklist

## 1. Pre-release Checklist

- [ ] Code merged and no unresolved conflicts *(manual)*
- [ ] `backend/.env` configured for target environment *(manual)*
- [ ] `APP_ENV=prod` in production *(manual)*
- [ ] `JWT_SECRET_KEY` replaced with strong random value *(manual)*
- [ ] `DATABASE_URL` points to production database *(manual)*
- [ ] `REDIS_URL` points to production redis *(manual)*
- [ ] `AUTO_CREATE_TABLES=false` in production *(manual)*
- [ ] `CELERY_TASK_ALWAYS_EAGER=false` in production *(manual)*
- [x] DB backup completed *(auto-checked locally: sqlite backup files created)*
- [x] `alembic upgrade head` completed *(auto-checked locally after `alembic stamp head`)*
- [x] Backend health endpoint reports DB/Redis OK *(auto-checked: `http://127.0.0.1:8001/health`)*
- [x] Smoke test passed *(auto-checked: `BASE_URL=http://127.0.0.1:8001 ./scripts/smoke-test.sh`)*

## 2. Release Steps

### Option A: Local process mode

1. Install dependencies:
   - `make backend-install`
2. Run migration:
   - `make backend-migrate`
3. Start API:
   - `make backend-run`
4. Start worker:
   - `make worker`
5. Start frontend:
   - `make frontend-install`
   - `make frontend-dev`

### Option B: Docker Compose mode

1. Build and start:
   - `docker compose up -d --build`
2. Verify:
   - `curl -sS http://<host>:8000/health`
3. Smoke test:
   - `BASE_URL="http://<host>:8000" ./scripts/smoke-test.sh`

## 3. Post-release Verification

- [x] Login works *(auto-checked locally)*
- [x] Create competitor works *(auto-checked locally; idempotent 409 for existing record)*
- [x] Create activity works *(auto-checked locally)*
- [x] Notifications API works with pagination *(auto-checked locally)*
- [ ] No 5xx spikes in logs *(manual runtime observation needed)*
- [ ] Celery worker receives tasks *(manual worker/log check needed)*

## 3.1 Verification Notes (2026-04-09)

- Local verification base URL: `http://127.0.0.1:8001`
- `pytest` result: `1 passed`
- Smoke test result: passed
- Migration alignment:
  - backup created: `backend/hotel_monitor.db.bak.*`
  - executed: `cd backend && PYTHONPATH=. .venv/bin/alembic stamp head`
  - verified: `cd backend && PYTHONPATH=. .venv/bin/alembic upgrade head`

## 4. Rollback Plan

If release fails:

1. Stop new app/worker processes
2. Restore previous app version
3. Restore previous env config
4. If schema incompatible, restore DB snapshot
5. Restart old app and worker
6. Re-run health check and smoke test on old version

## 5. Troubleshooting Quick Guide

### Symptom: `/health` degraded

- Check DB connectivity:
  - verify `DATABASE_URL`
  - verify DB instance is up
- Check redis connectivity:
  - verify `REDIS_URL`
  - verify redis service is up

### Symptom: login/register returns 500

- Check backend logs for traceback
- Verify password hashing dependency is installed
- Verify DB schema has `users` table

### Symptom: extension report accepted but no alerts

- Verify alert rules exist and active
- Verify at least 2 price points exist for same competitor
- Verify worker is running (`CELERY_TASK_ALWAYS_EAGER=false` mode)

### Symptom: notifications empty

- Confirm alerts were generated in `alert_records`
- Verify pagination params (`page`, `page_size`)
