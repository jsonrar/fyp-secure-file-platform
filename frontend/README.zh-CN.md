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
| `/forgot-password` | 使用邮箱验证码重置登录密码 |
| `/dashboard` | 登录后工作台 |
| `/upload` | 文件加密上传（需要身份认证） |
| `/files` | 文件管理（需要身份认证） |
| `/audit-logs` | 审计访问记录（需要身份认证） |
| `/admin` | 有限的管理/恢复概览（需要身份认证） |
| `/education` | 教育页面 |
| `/help` | 产品帮助 — 链到首页图文引导；视频占位 |
| `/team` | Contact us — 反馈表单预览 + 开发团队 |

## 结构

- `src/components/securfile/` — 从 SecurFile 迁移的 UI
- `src/api/` — 与后端 `/api/v1` 对齐的 Axios 客户端
- `src/crypto/` — 认证文件加解密及分享密钥重包装
- `src/stores/` — Pinia 身份认证／文件状态
- `src/composables/useTheme.ts` — 系统／明亮／暗色主题

浏览器已经实现账户密钥登记、passphrase／私钥文件解锁、加密上传、认证下载与本地解密、分享
密钥重包装、撤销、搜索、审计历史、refresh 轮换、登出及注销账户。修改 passphrase、后继密钥
轮换及完整的角色感知管理/恢复界面仍属于 backlog。

在 `/files` 中，**Download encrypted** 无需解锁账户密钥即可将原始密文保存为
`<filename>.ciphertext`；**Download and decrypt** 仍在需要时弹出解锁对话框并保存原文件。
两者均使用已认证且校验完整性的 `POST /files/{file_id}/download` 端点。密文下载只包含存储的
blob，不包含离线解密所需的完整 envelope。

## 环境变量

默认 API 地址已是 `http://localhost:8000/api/v1`。如需覆盖，请创建不纳入版本管理的
`frontend/.env.local`：

```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
```
