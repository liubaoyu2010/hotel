# Hotel Monitor MVP

基于《可执行版 v2》的项目代码仓骨架，目标先完成 P0 可运行闭环：

- 用户认证（注册/登录）
- Extension 注册与上报链路
- 竞品管理与房价概览接口
- 活动日历查询接口（先占位）

## 目录结构

- `backend/` FastAPI 后端
- `frontend/` 前端占位（后续 Vue 3）
- `extension/` Chrome Extension 占位（后续 MV3）

## 快速开始（后端）

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Docker 启动基础依赖

```bash
docker compose up -d postgres redis
```

## 常用命令（Makefile）

```bash
make backend-install
make backend-migrate
make backend-run
make worker
make frontend-install
make frontend-dev
```

健康检查：

- `GET /health`（包含 DB/Redis 子状态）
- `./scripts/smoke-test.sh`（上线后冒烟验证）
- `RELEASE_CHECKLIST.md`（上线前检查/回滚/故障排查）

启动后访问：

- `http://127.0.0.1:8000/health`
- `http://127.0.0.1:8000/docs`
- `http://127.0.0.1:5173`（前端开发页面）

## 说明

当前已进入第二阶段：

- 后端具备持久化、JWT、竞品管理、Extension上报入库
- 已提供 Alembic 迁移骨架与基础 API 测试
- 任务队列、活动采集、前端页面将继续按模块补齐

当前前端已提供：

- 用户端：登录/注册、仪表盘、竞品、活动、告警规则、通知、扩展设备与上报、个人中心
- 后台端（admin）：系统用户管理、审计日志

## 上线最短路径（5条命令）

适用于本机快速拉起并完成最小验收：

```bash
docker compose up -d postgres redis
make backend-install
cd backend && PYTHONPATH=. .venv/bin/alembic upgrade head && cd ..
PYTHONPATH=backend backend/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8001
BASE_URL=http://127.0.0.1:8001 ./scripts/smoke-test.sh
```

如果第 3 步遇到 `table already exists`，按 `DEPLOY.md` 的 “Existing DB safety path” 执行：

- 先备份 DB
- `alembic stamp head`
- 再 `alembic upgrade head`

## 10分钟联调指引（后端 + 扩展）

目标：确认扩展到后端的最小链路可用（登录 -> 绑定 -> 上报）。

### 1) 启动后端（建议 8001）

```bash
docker compose up -d postgres redis
make backend-install
cd backend && PYTHONPATH=. .venv/bin/alembic upgrade head && cd ..
PYTHONPATH=backend backend/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8001
```

### 2) 加载扩展

1. Chrome 打开 `chrome://extensions`
2. 开启开发者模式
3. 点击“加载已解压的扩展程序”
4. 选择项目目录下 `extension/`

### 3) 在扩展 Popup 里完成最小闭环

1. API Base 选 `http://127.0.0.1:8001`
2. 点击 `1) Login`
3. 点击 `2) Bind Extension`
4. 点击 `3) Report Test Data`
5. 观察输出中 `processed_count` 与状态提示

### 4) 验收标准

- 后端 `GET /health` 返回 `code=200`
- Popup 的 login / bind / report 都成功
- `Unmatched Competitors`、`Last Auto Report` 有可读数据
- `./scripts/smoke-test.sh` 通过
