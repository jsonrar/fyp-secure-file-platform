# Changelog / 更新日志

All notable changes to this project are documented in this file.

本文件记录此项目的所有重要变更。

## [Unreleased] / [未发布]

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
