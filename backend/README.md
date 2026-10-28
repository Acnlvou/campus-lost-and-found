# 后端（backend）

基于 Python、FastAPI、SQLAlchemy 和 Alembic 的 API 服务。当前包含 FastAPI 应用入口、版本化 API 路由、健康检查、环境配置、CORS 和数据库会话/迁移基础设施；登录、失物/招领发布、检索和认领审核等业务模块仍是预留目录，尚未实现。

## 架构

```text
backend/
├── app/
│   ├── main.py                 # FastAPI 应用、CORS 和路由装配
│   ├── api/
│   │   ├── router.py           # API 路由总入口
│   │   └── routes/health.py    # /api/v1/health 健康检查
│   ├── core/config.py          # 环境变量与应用设置
│   ├── db/
│   │   ├── base.py             # SQLAlchemy 声明式模型基类
│   │   └── session.py          # Engine、Session 与请求级数据库依赖
│   └── modules/                # auth、items、claims、notifications 业务模块
├── alembic/                    # 数据库迁移环境与版本脚本
├── config/                     # 配置说明
├── data/runtime/               # 本地运行数据；数据库文件不会提交
├── pyproject.toml              # Python 依赖与 FastAPI CLI 入口
└── uv.lock                     # 锁定依赖版本
```

API 统一挂载在 `/api/v1`。本地 Vue 开发源 `http://localhost:5173` 已加入默认 CORS 白名单，可通过 `CAMPUS_FRONTEND_ORIGINS` 调整。不要使用宽泛的通配来源处理带凭据的请求。

本地数据库默认使用 SQLite，地址由 `CAMPUS_DATABASE_URL` 配置。SQLAlchemy 和 Alembic 已就位，但当前没有业务模型或迁移版本；并发认领、唯一约束和审计记录需要在需求与数据模型明确后实现。SQLite 默认值用于本机启动，不代表生产数据库选型。

## 环境要求

- Python 3.11 或更高版本
- [uv](https://docs.astral.sh/uv/)

## 安装与启动

在仓库根目录执行：

```sh
cd backend
cp .env.example .env
uv sync
uv run fastapi dev
```

开发服务器默认监听 `http://127.0.0.1:8000`。停止服务按 `Ctrl+C`。

## 当前接口

- `GET /`：返回服务名称和 API 文档路径。
- `GET /api/v1/health`：返回 `{"status":"ok"}`。
- `/docs`：Swagger UI；`/redoc`：ReDoc；`/openapi.json`：OpenAPI schema。

## 常用命令

```sh
cd backend
uv run fastapi dev       # 开发服务，自动重载
uv run fastapi run       # 运行服务，不启用自动重载
uv run alembic current   # 查看数据库迁移版本
```

业务端点、认证和数据库迁移尚未实现；当前仅作为可启动的后端基础骨架。
