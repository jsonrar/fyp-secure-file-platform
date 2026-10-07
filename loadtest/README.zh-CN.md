# SecureView 压力测试

[English](README.md) | 简体中文

一个行为与浏览器一致的客户端：每次上传都用真实的文件信封加密，每次下载都解密并校验 SHA-256，同时为每个
操作计时。

- 测试计划、已知限制、发现和完整流程：[`docs/PERFORMANCE_TESTING.zh-CN.md`](../docs/PERFORMANCE_TESTING.zh-CN.md)。
- 针对一次性环境的本地演练：`bash loadtest/run_local.sh`（需要指向 `_test` 数据库的 `DB_*`）。
- 测试：`.venv/bin/python -m pytest tests`。
- 结果：[`docs/performance/REPORT-2026-10-03.md`](../docs/performance/REPORT-2026-10-03.md)（staging，2026-10-03/04），
  以及 100 用户问题的修复和 staging 重测
  [`docs/performance/pool-fix-2026-10-04/`](../docs/performance/pool-fix-2026-10-04/README.zh-CN.md)。

| 文件 | 作用 |
| --- | --- |
| `secureview_load/envelope.py` | 浏览器的文件信封（AAD-3、AES-128/192/256-GCM 与 ChaCha20-Poly1305、RSA-OAEP），以 `docs/crypto/test_vectors.json` 为准。这里未实现 AES-256-GCM-SIV 和 XChaCha20-Poly1305；压测使用 AES-256-GCM |
| `secureview_load/client.py` | 通过公开 API 操作的一个虚拟用户 |
| `secureview_load/runner.py` | 场景：`smoke`、`steps`、`parallel`、`mixed`、`sizes`、`logins` |
| `secureview_load/report.py` | Markdown 报告和图表，与服务器采样数据对齐 |
| `server_sampler.py` | 用系统 Python 在服务器上运行：CPU、内存、磁盘、网络、进程和连接数 |
| `../backend/scripts/seed_load_users.py` | 在服务器上创建测试账户 |

未告知团队前，不要把它指向共享服务器；除非加上 `--confirm-remote`，它会拒绝非本地主机。
