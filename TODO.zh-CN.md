# SecureView 优先级 Backlog

[English](TODO.md) | [简体中文](TODO.zh-CN.md)

本文件最初于 2026-09-03 根据 GitHub `main`、共享 changelog、仓库测试及线上预发布环境
完成同步。2026-09-07 再次对照 GitHub `main` 的 `cab44b1` 检查；该版本已合并 500 MiB
上传上限改动，但本次仅同步 backlog，未重新核验线上部署。GitHub Issues 是可执行 backlog，
团队通过 [SecureView Development Board](https://github.com/users/Waldo0926/projects/1)
共用 Kanban 视图；本文件只提供带链接的优先级摘要，不再成为另一份会漂移的清单。

下方已交付 MVP 能力继续保持勾选。当前 GitHub `main` 尚未完整满足下方未勾选 Issue
（#52–#60 与 #71–#76）的整体验收目标：其中部分已有基础实现，但仍缺 CI、运维证据、
角色感知 UI 或本次新增的产品流程，因此不会把“部分完成”误标为完成。

提案对照结果记录在 [`docs/PROPOSAL_TRACEABILITY.md`](docs/PROPOSAL_TRACEABILITY.md)：
24 个 WBS 工作包中 20 个 Done、3 个 In progress、1 个 Backlog；7 条产品验收标准中 6 条
Done，剩余的分阶段进度提示为 In progress。
M3 已依据导师看过并签署确认的 MVP/UI 检查点标为 Done；导师所说的全项目约 70–80%
是该历史检查点的判断，不是对当前完成度的精确测量。

## 已交付 MVP 基线

待评审的本地预览：How it works 新增六步带定位标记的截图引导，支持手动切换、可选播放和放大。
详见 [截图引导记录](changelog/CHANGELOG.md#homepage-screenshot-walkthrough--首页截图操作引导)。
截图脚本使用模拟后端响应，不代表
[#58 浏览器 E2E 覆盖](https://github.com/jsonrar/fyp-secure-file-platform/issues/58)
已完成，也不构成部署证据。

当前 GitHub `main`（本次同步未重新核验线上部署）：Core Features 已修复宽屏周期交界处
的空白跳闪，保留悬停暂停，并在减少动态效果模式下静态展示全部卡片。详见 [实现记录](changelog/CHANGELOG.md#landing-hero-and-feature-marquee-polish--首页主标题与功能滚动条打磨)。
此 UI 修复不代表 [#58 浏览器 E2E 覆盖](https://github.com/jsonrar/fyp-secure-file-platform/issues/58)
已经完成；线上部署核验与可重复的浏览器覆盖仍按各自验收条件推进。

- [x] 邮箱验证码注册与重置登录密码、登录与浏览器本地登出、后端会话撤销端点、refresh 轮换、
  会话失效、注销账户、限流、
  Argon2id 密码哈希与 RBAC。
- [x] 浏览器持有的账户密钥登记、passphrase/私钥文件解锁、空闲自动上锁及历史密钥 bundle
  获取；明文私钥不会提交到服务器。
- [x] 浏览器端 AES-128/192/256-GCM 与 ChaCha20-Poly1305 文件加密、RSA-OAEP-SHA256 DEK
  包装、认证下载/解密、完整性失败提示及密文存储。
- [x] 文件名搜索、分页、所有者/被分享文件分区、接收者密钥重包装共享、接收者列表、撤销、通知、
  逐文件历史，以及基于所有权的正确审计可见性。
- [x] 条件恢复与管理 API、防篡改审计链、MySQL 最小权限生产 SQL、HTTPS、nginx 限流、
  fail2ban、受保护自动部署及对账实现。
- [x] 公网预发布与评审入口：[应用](https://secureview.tech)、
  [Swagger UI](https://secureview.tech/docs)、
  [OpenAPI JSON](https://secureview.tech/openapi.json)。
- [x] 公开产品页与登录后账户壳层：落地页 `/`、Education（`/education`：算法、演练场、知识库）、
  Help（`/help`：How to Use 操作演示）、Contact us（`/team`：反馈表单预览 + 团队拼贴）、页头当前标签主题色高亮，
  以及含 `/profile` 与 `/settings` 的头像菜单。证据与理由见
  [`changelog/CHANGELOG.md`](changelog/CHANGELOG.md) 的 `[Unreleased]`。

已交付行为的原因和证据统一写在
[`changelog/CHANGELOG.md`](changelog/CHANGELOG.md)，不再复制进历史 TODO。

## 2026-09-03 同步前已核验基线

| 门禁 | 结果 | 含义 |
| --- | --- | --- |
| 后端 Pytest | 317 passed, 21 skipped, 1 warning | 单元/API 通过；真实 MySQL 覆盖未运行 |
| 前端 Vitest | 233 passed, 18 skipped | 离线套件通过；集成覆盖被跳过 |
| 前端 typecheck | 通过 | `vue-tsc --noEmit` 可正常运行 |
| 前端 production build | 通过 | Vite 生产 bundle 构建成功 |
| Ruff format/check | **失败** | 4 个文件需格式化，3 个 import block 不合规 |
| GitHub Actions | **不存在** | 当前没有 required CI gate 保护 `main` |
| Schema 基线 | `0006_chacha20_poly1305` | 生产 SQL 共 17 张表 |
| 线上预发布 | `a085ae4`（PR #51，本次文档同步前） | `/`、health、docs、schema、ReDoc 均为 200 |

带 integration skip 的测试只证明离线子集，不得表述为发布通过。

## P0 — 发布与数据保护阻塞项

- [x] [#52 建立 required CI 门禁并修复当前 Ruff 基线](https://github.com/jsonrar/fyp-secure-file-platform/issues/52)
  ——`.github/workflows/ci.yml` 在每个 PR 及推送到 `main` 时运行 backend（Ruff + 不依赖 MySQL 的
  pytest）与 frontend（测试/类型检查/构建）；Ruff 基线已真正修复而非压制。分支保护仍需仓库管理员
  将 `backend`、`frontend` 设为必需检查——详见引入本改动的 PR。
- [ ] [#53 在 CI 中运行完整 MySQL 8.4 与 Schema parity 门禁](https://github.com/jsonrar/fyp-secure-file-platform/issues/53)
  ——`mysql-gate` Job 拉起经 TLS 校验的 MySQL 8.4，执行到 `0006_chacha20_poly1305` 的每一次迁移，
  运行 `alembic current`/`check`，任何集成测试被跳过即判失败，并检查运行时账户与管理员账户的权限
  边界及线上 Schema 一致性。遗留：并发加锁与部分 DDL 恢复检查目前是普通脚本断言，而非模糊测试或
  混沌测试；备份恢复演练比对的是表数与行数，而非完整校验和。
- [ ] [#56 自动化加密异地备份并证明可在洁净主机恢复](https://github.com/jsonrar/fyp-secure-file-platform/issues/56)
  ——定义 RPO/RTO，协调数据库/密文备份并保留恢复证据。
- [x] [#61 保持 README、TODO、Issues、changelog、PR 与部署同步](https://github.com/jsonrar/fyp-secure-file-platform/issues/61)
  ——本次同步 PR 建立统一记录与证据清单；后续变更沿用同一规则。

## P1 — 补全已有后端能力与运维

- [ ] [#54 完成浏览器修改 passphrase 与后继密钥轮换](https://github.com/jsonrar/fyp-secure-file-platform/issues/54)
  ——使用带签名的后端契约，并发布规范化账户信封文档。
- [ ] [#55 完成管理员、恢复专员及审计验证流程](https://github.com/jsonrar/fyp-secure-file-platform/issues/55)
  ——通过角色感知 UI 演示现有 RBAC/恢复/审计 API。
- [ ] [#57 安全验证并启用 staging 对账 timer](https://github.com/jsonrar/fyp-secure-file-platform/issues/57)
  ——启用定时删除前必须审查 report-only 输出。
- [ ] [#58 扩展浏览器 E2E、并发、故障注入与覆盖率门禁](https://github.com/jsonrar/fyp-secure-file-platform/issues/58)
  ——把跳过/依赖线上环境的覆盖转成必跑、可重复证据。
- [ ] [#59 增加脱敏可观测性、事故 runbook 与外部审计 checkpoint](https://github.com/jsonrar/fyp-secure-file-platform/issues/59)
  ——让运维和审计失败可见，同时不泄露 Secret。

## P2 — 正式安全保障

- [ ] [#60 完成正式威胁模型与独立安全评审](https://github.com/jsonrar/fyp-secure-file-platform/issues/60)
  ——覆盖账户信封、Argon2id、token/密钥托管、metadata、恢复、CSP、依赖及残余信任边界，
  且不得声称已经认证。

## P3 — 计划中的产品 UX

已于 2026-09-07 拆成可执行 Issue 并加入共享 backlog。各项部分实现状态见下文；邻近的 UI
打磨不得视为这些项已完成。每个 Issue 均按
[#61](https://github.com/jsonrar/fyp-secure-file-platform/issues/61) 写明验收标准。

- [ ] [#72 高危与破坏性操作二次确认](https://github.com/jsonrar/fyp-secure-file-platform/issues/72)
  ——删除文件、撤销分享、注销账户及同类高影响操作使用独立弹窗，明确目标、后果与是否可恢复，
  不再由单击图标直接触发。
- [ ] [#71 认证后的密文预览与加密文件下载](https://github.com/jsonrar/fyp-secure-file-platform/issues/71)
  ——授权用户可查看有限长度的密文预览或保存服务器实际存储的加密对象；不得静默解密，也不改变
  现有明文解密下载流程。
  分支 `feat/download-encrypted-file` 已实现所有者和授权接收者无需 passphrase 的密文下载。
  密文预览和部署核验仍待完成；本次部分实现不会关闭 #71。
- [ ] [#73 My Files 文件架与移动功能](https://github.com/jsonrar/fyp-secure-file-platform/issues/73)
  ——创建所有者专属文件架，并在文件架与根目录之间移动自己的文件；不改变加密、分享、文件身份
  或审计语义。
- [ ] [#54 浏览器修改 passphrase、密钥文件重置与后继密钥轮换](https://github.com/jsonrar/fyp-secure-file-platform/issues/54)
  ——密钥文件重置已完成：Settings 会用账户公钥验证保存的私钥文件，在新 AMK 与新 passphrase 下重新
  封装它，并以 RSA-PSS 签名证明持有；明文私钥不离开浏览器。仍待完成：在记得旧 passphrase 时修改
  passphrase、后继密钥轮换，以及账户信封规范文档。本次部分实现不关闭 #54。
- [ ] [#74 持久化 English / 简体中文语言切换](https://github.com/jsonrar/fyp-secure-file-platform/issues/74)
  ——产品语言可由用户选择，具备完整 key 覆盖、安全 fallback、偏好持久化与手机端可用控件。
- [ ] [#75 经验证的用户头像上传与展示](https://github.com/jsonrar/fyp-secure-file-platform/issues/75)
  ——资料页 / 页头支持可选头像，并包含内容验证、安全提供、清理、限流及首字母 fallback。
- [ ] [#76 修复手机与窄屏下的产品流程](https://github.com/jsonrar/fyp-secure-file-platform/issues/76)
  ——修复公开页面、账户与文件流程在窄屏下的布局和交互问题，并保留可重复的手机浏览器证据。

## 每个 Issue 的完成定义

- 实现与测试满足 Issue 验收标准。
- 经过评审的 PR 链接 Issue，并更新双语 changelog。
- 当功能描述改变时同步 README/TODO 和设计文档；不适用则在 PR 中说明 `N/A`。
- 所有成员统一使用共享 Changelog，不再新增或续写个人/分轨变更日志。
- 合并前通过 Secret 与生成物检查。
- 运行时改动必须由自动部署到达准确 merge SHA，并验证健康检查与受影响用户流程；仅 merge
  不代表部署完成。
- 上述证据全部链接后才关闭 Issue。

## 当前 FYP 明确延期项

- Google Drive 式协同编辑、加密全文搜索及大规模对象存储优化。
- 保证支持 1 GB 以上文件。
- 阻止接收者继续使用已经复制的数据等 DRM 能力。
- 正式生产 KMS/HSM 实现和独立认证；其设计与托管要求仍属于安全评审范围。
