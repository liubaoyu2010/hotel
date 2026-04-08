# Backend (FastAPI)

当前版本为 P0 第一阶段可运行实现，已接入：

- SQLAlchemy 持久化（默认 SQLite，可通过 `DATABASE_URL` 切换）
- JWT 登录鉴权
- 竞品创建/列表
- Extension 注册与数据上报（Token校验）
- 活动创建与日历查询
- Celery 异步任务触发与状态查询
- 告警规则与告警记录查询

## Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## 迁移

```bash
alembic upgrade head
```

## 测试

```bash
pytest -q
```

## 现有接口

- `GET /health`
- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/extension/register`
- `POST /api/v1/extension/report`
- `POST /api/v1/competitors`
- `GET /api/v1/competitors`
- `GET /api/v1/competitors/{id}/price-history`
- `GET /api/v1/dashboard/price-overview`
- `POST /api/v1/activities`
- `GET /api/v1/activities/calendar`
- `POST /api/v1/alert-rules`
- `GET /api/v1/alert-rules`
- `PUT /api/v1/alert-rules/{id}`
- `DELETE /api/v1/alert-rules/{id}`
- `GET /api/v1/alerts`
- `GET /api/v1/notifications`
  - 支持分页参数：`page`（默认1）、`page_size`（默认20，最大100）
- `GET /api/v1/competitor-aliases`
- `PUT /api/v1/competitor-aliases`
- `POST /api/v1/tasks/alert-check`
- `GET /api/v1/tasks/status/{task_id}`

## 下一步

- 切换 PostgreSQL + TimescaleDB
- 增加 Alembic 迁移
- 接入 Celery + Redis 异步告警链路

## 启动 Celery Worker（本地）

```bash
celery -A app.celery_app.celery_app worker --loglevel=info
```

## 备注

- 默认通过 Alembic 管理建表。仅在 `AUTO_CREATE_TABLES=true` 时会在启动时自动建表。
- 全局异常响应已统一为：
  - `{"code": <http_status>, "message": "<error>", "data": {}}`
  - 参数校验错误为 `code=422`，详情在 `data.errors`
- `GET /health` 增加子检查：
  - `checks.database`
  - `checks.redis`
