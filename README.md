# 校园失物招领系统

面向校园失物与招领信息发布、检索和认领的 Web 项目。前端采用 Vue 3、TypeScript 和 Vite；后端采用 Python、FastAPI、SQLAlchemy 和 Alembic。

## 当前状态

目前已搭好前后端基础骨架：前端保留 Vue 官方欢迎界面；后端提供根路由、`/api/v1/health` 健康检查、CORS 配置，以及 SQLAlchemy/Alembic 基础设施。前后端尚未实现失物招领业务页面或业务 API，也没有业务数据模型和数据库迁移。

课程需求基线计划包含演示账户登录、失物/招领信息发布、组合检索、认领申请、发布者审核和并发一致性控制。图片上传、站内通知、校园真实身份认证和后台管理属于后续范围；最终实现范围以评审通过的 SRS 为准。

## 仓库结构

```text
.
├── backend/    # FastAPI 服务、配置、数据访问和 Alembic 迁移
├── deploy/     # 部署说明及平台原生资源
├── docs/       # 开发文档、需求和课程交付材料
├── front/      # Vue Web 单页前端
├── scripts/    # 开发和数据维护辅助脚本
└── .vscode/    # 仓库级编辑器配置
```

## 环境要求

- Node.js：`^22.18.0` 或 `>=24.12.0`，npm 随 Node.js 安装
- Python：3.11 或更高版本
- [uv](https://docs.astral.sh/uv/)：Python 环境和依赖管理

## 启动开发环境

分别在两个终端窗口中运行前端和后端。

终端一，在仓库根目录执行：

```sh
cd front
npm install
npm run dev
```

Vite 默认地址为 `http://localhost:5173/`，以终端输出为准。

终端二，在仓库根目录执行：

```sh
cd backend
cp .env.example .env  # 首次启动时创建本地配置
uv sync
uv run fastapi dev
```

FastAPI 默认地址为 `http://127.0.0.1:8000/`。交互式 API 文档位于 `http://127.0.0.1:8000/docs`，健康检查为 `http://127.0.0.1:8000/api/v1/health`。后端默认 CORS 来源是 `http://localhost:5173`；本地配置可通过 `CAMPUS_FRONTEND_ORIGINS` 调整。

## 前端生产构建

```sh
cd front
npm run build
```

构建产物写入 `front/dist/`。后端本地 SQLite 数据库地址可通过 `CAMPUS_DATABASE_URL` 设置；SQLite 当前只作为开发默认值，生产数据库和部署配置尚未确定。

## 架构边界

- 浏览器前端只通过 HTTP API 与后端通信，不直接连接数据库。
- FastAPI 路由统一使用 `/api/v1` 前缀；接口文档由 FastAPI 根据路由生成。
- 登录身份、数据所有权、认领审核及并发状态约束应由服务端和数据库负责，不能依赖前端校验。
- 目前 `auth`、`items`、`claims` 等目录是业务模块预留位置，尚无对应实现。
