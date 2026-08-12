# Changelog / 更新日志

All notable changes to this project are documented in this file.

本文件记录此项目的所有重要变更。

## [Unreleased] / [未发布]

### Deployment operations / 部署运维

- Added the versioned server-pull automatic deployment command and systemd units for the
  MCS21 staging VPS. The timer deploys an exact `main` commit through the guarded release
  command and quarantines a failed SHA instead of retrying it continuously.
- 已加入 MCS21 预发布 VPS 的服务器拉取自动部署命令与 systemd 单元。Timer 会通过带保护措施
  的发布入口部署准确的 `main` commit，并隔离失败 SHA，避免持续重复部署坏版本。
- Documented the pull-request-to-release workflow, read-only Deploy Key boundary, operator
  commands, database safety boundary, rollback behavior, and audit path in English and Chinese.
- 已用中英文记录从 Pull Request 到发布的流程、只读 Deploy Key 边界、队员命令、数据库安全
  边界、回滚行为及审计路径。
- Versioned the guarded release implementation and fixed completed-release permissions so the
  unprivileged `fypapp` and Nginx identities can execute/read artifacts created after source
  extraction. The failed preflight remained on the prior healthy release and the corrected
  retry passed.
- 已将带保护措施的发布实现纳入版本管理，并修复完整 release 的最终权限，使无特权
  `fypapp` 与 Nginx 身份可执行／读取源码解压后才生成的文件。首次预检失败期间仍保持旧健康
  版本运行，修复后的重试已经通过。
- Treat scheduled skips of an already-quarantined SHA as a healthy no-op while retaining the
  original deployment failure in the journal and audit log.
- 已隔离 SHA 的后续定时跳过现在属于健康的无操作；原始部署失败仍保留在 journal 与审计日志
  中，不再每两分钟制造重复的 systemd 失败。

### Development environment / 开发环境

- Created the `CT-1.0` development branch for upcoming cryptography work.
- 已创建用于后续密码学工作的 `CT-1.0` 开发分支。
- Created the project-local Python virtual environment at `backend/.venv`.
- 已在 `backend/.venv` 创建项目本地 Python 虚拟环境。
- Installed the repository-pinned `pytest` 9.1.1 and `cryptography` 50.0.0 packages.
- 已安装仓库锁定版本的 `pytest` 9.1.1 和 `cryptography` 50.0.0。

### Scope note / 范围说明

- No application or cryptographic implementation code was changed in this update.
- 本次更新未修改应用程序代码或密码学实现代码。

update:2026/8/12 14:48

-------------------------------------------------------------------------------------------------------------
## CT-1.1

### Baseline / 基线

- Created `CT-1.1` from the merged `main` commit `9593e75`.
- 已从完成合并的 `main` 提交 `9593e75` 创建 `CT-1.1`。
- Verified the existing cryptography baseline with
  `python -m pytest tests/unit/test_crypto_service.py -q --durations=10`:
  4 tests passed in 0.54 seconds.
- 已使用 `python -m pytest tests/unit/test_crypto_service.py -q --durations=10`
  验证现有密码学基线：4 项测试全部通过，耗时 0.54 秒。

### Confirmed limitations / 已确认限制

- AES-GCM encryption currently processes the complete plaintext in memory and does not
  authenticate associated data (AAD).
- 当前 AES-GCM 加密会在内存中处理完整明文，且未认证关联数据（AAD）。
- No versioned encrypted-envelope format or streaming encryption interface exists yet.
- 当前尚无带版本的密文封装格式或流式加密接口。
- No cryptographic implementation code was changed during this baseline step.
- 本基线步骤未修改任何密码学实现代码。

update: 2026/8/12 17:27
