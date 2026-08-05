# 前端

[English](README.md) | [简体中文](README.zh-CN.md)

集成 SecurFile UI 和 FYP 后端 API 的 Vue 3 + TypeScript 前端。

## 运行

```bash
npm install
npm run dev
```

后端应运行于 `http://localhost:8000`。

## 页面

| 路由 | 说明 |
|-------|-------------|
| `/` | 落地页（主视觉区 + 功能介绍） |
| `/login` | 登录 |
| `/register` | 注册 + 显示私钥 |
| `/upload` | 文件加密上传（需要身份认证） |
| `/files` | 文件管理（需要身份认证） |
| `/audit-logs` | 审计访问记录（需要身份认证） |
| `/admin` | 管理面板（需要身份认证） |
| `/community` | 教育页面 |
| `/team` | 开发团队页面 |

## 结构

- `src/components/securfile/` — 从 SecurFile 迁移的 UI
- `src/api/` — 与后端 `/api/v1` 对齐的 Axios 客户端
- `src/stores/` — Pinia 身份认证／文件状态
- `src/composables/useTheme.ts` — 明亮／暗色主题

## 环境变量

复制 `.env` 并按需调整：

```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
```
