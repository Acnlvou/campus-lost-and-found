# 前端（front）

基于 Vue 3、TypeScript 和 Vite 的浏览器端单页应用。当前保留 Vue 官方脚手架的欢迎界面，用于确认前端依赖安装和生产构建流程；尚未接入失物招领业务页面、FastAPI 接口、路由或状态管理。

## 前端架构

```text
front/
├── index.html                 # Web 应用 HTML 入口
├── public/                    # 原样复制到构建产物的公共静态资源
├── src/
│   ├── main.ts                # 加载全局样式并挂载 Vue 应用
│   ├── App.vue                # 根组件；当前显示 Vue 官方欢迎界面
│   ├── components/            # 欢迎页组件与图标组件
│   └── assets/                # 由 Vite 处理的样式和图片
├── vite.config.ts             # Vue 插件、开发工具插件和 @ -> src 路径别名
├── tsconfig*.json             # TypeScript 配置
├── package.json               # 依赖及 npm 脚本
└── package-lock.json          # npm 依赖锁定文件
```

`npm run build` 会并行运行 `vue-tsc --build` 类型检查和 `vite build`，生成 `dist/`。`npm run preview` 可在本地预览该构建结果。当前 Vite 配置尚未设置 FastAPI 开发代理；接入后端时应在前端 API 模块中统一管理请求，并配置明确的开发 API 地址。

## 环境要求

- Node.js：满足 `package.json` 中的版本范围 `^22.18.0 || >=24.12.0`
- npm：随 Node.js 安装

可以先用以下命令确认本机版本：

```sh
node -v
npm -v
```

## 启动开发服务器

在仓库根目录执行：

```sh
cd front
npm install
npm run dev
```

按终端显示的地址打开页面，Vite 默认地址通常是 `http://localhost:5173/`。开发服务器支持热更新。

## 检查与生产构建

```sh
cd front
npm run type-check
npm run build
```

构建产物位于 `front/dist/`。如需在本机查看生产构建：

```sh
npm run preview
```
