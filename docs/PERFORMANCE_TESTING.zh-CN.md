# 性能与容量测试

[English](PERFORMANCE_TESTING.md) | [简体中文](PERFORMANCE_TESTING.zh-CN.md)

2026-10-01 的会议上，导师要的是数字，而不是“支持多人同时使用”：服务器能承受多少用户、多少文件、多大的文件，
以及在哪里开始出问题（会议行动项第 4、5、6 项）。本文是测试计划、测试工具、开测前就已知的上限，以及本地预演发现的问题。

**状态（2026-10-02）：** 工具已完成，并在本地环境端到端跑通。针对 staging 服务器的正式测试**还没有进行**：
服务器正在跑另一项任务，和别的负载抢 CPU 与网络时测出的数字是错的。下文没有任何一项是 staging 的测量结果。
正式测试由 [#140](https://github.com/jsonrar/fyp-secure-file-platform/issues/140) 跟踪。

## 测的是什么，服务器实际做了什么

SecureView 在浏览器里加密。服务器从不加密或解密文件：上传时它校验信封、边写盘边计算哈希，并在一个事务里写入元数据、
授权、密钥包装和一条哈希链审计记录；下载时边传输边复核存储的 SHA-256，并追加一条审计记录。所以报告里的“加密耗时”是
**客户端**的耗时（由压测工具测量，它做的工作和浏览器完全一样），服务器的开销是 I/O、哈希、数据库事务和审计链。

压测工具（`loadtest/`）的行为和浏览器完全一致：每次上传都用同样的 AAD 绑定信封加密（与浏览器加密库自己的已知答案向量
`docs/crypto/test_vectors.json` 对齐），**每次下载都会解密并用 SHA-256 与原文件比对**。所以每一次操作都同时证明了数据完整，而不只是速度。

## 开测前已知的上限

这些来自代码和服务器配置，决定了任何测试能测出的上限：

| 上限 | 数值 | 对测试的影响 |
| --- | --- | --- |
| 服务器 | 8 vCPU、16 GB 内存、387 GB 磁盘（剩余 237 GB） | 硬件天花板 |
| API 进程 | 只有一个 uvicorn 进程，没有 `--workers` | 所有 Python 工作共享一个解释器；同步接口在它的线程池里运行 |
| 数据库连接池 | SQLAlchemy 默认：5 个连接 + 10 个溢出 | API 同时最多 15 个数据库事务 |
| nginx，按来源 IP | API 每秒 10 个请求（突发 20）；登录每分钟 12 次（突发 8） | 从一台机器经 `https://secureview.tech` 压测，测到的是这个限制而不是服务器 |
| 密码哈希 | `AUTH_PASSWORD_HASH_CONCURRENCY=2`：同时最多两个 Argon2id（64 MiB）验证；第三个**立即返回 429**，不排队 | 超过 2 个的同时登录会失败，需要客户端重试 |
| 上传大小 | 明文 500 MiB（`MAX_UPLOAD_SIZE_BYTES`），nginx 请求体 501 MB，代理超时 300 秒 | 最大文件；网速慢时接近上限可能超时 |
| 访问令牌 | 30 分钟 | 长时间测试时工具会自动续期 |

## 本地预演发现的问题

最初几次本地运行就发现了两个并发 bug。两者都是 MySQL 死锁（错误 1213），用户看到的是 **HTTP 500**；都在后端代码里，
所以记录在这里和 [#139](https://github.com/jsonrar/fyp-secure-file-platform/issues/139)，没有在压测这项工作里顺手改：

1. **两个用户同时登录可能死锁。** `_enforce_session_limit` 执行
   `SELECT … FROM user_sessions WHERE user_id=? AND status='ACTIVE' FOR UPDATE`。在 MySQL 默认的 REPEATABLE READ 下，
   对一个还没有活动会话的用户，这条语句锁住的是 `idx_user_sessions_user_status` 里的*间隙*；两个这样的用户（比如最新注册的两个账户）
   锁住同一个间隙，各自的 `INSERT INTO user_sessions` 都在等对方，于是其中一个被回滚。在两用户运行的第二次登录上复现。
2. **下载和分享可能在审计链头上死锁。** InnoDB 的死锁报告显示：一个分享事务持有 `audit_chain_heads`（id 1），在写审计记录时
   要等一个 `users` 行的共享锁（外键检查）；一个下载事务持有该 `users` 行的排他锁，在等 `audit_chain_heads`。
   6 用户混合负载下，约 1,330 次操作中失败了 4 次（0.3%）。

这类故障只在并发下出现，这正是做压测的意义。MySQL 对 1213 的建议是应用重试事务；更彻底的修法（让任何路径都不会在持有用户行时
再去等链头，或对这些事务使用 READ COMMITTED）由后端负责人选择。staging 正式测试会测出在真实并发下它们出现的频率。

## 压力从哪里来

由于 nginx 按 IP 限流，选择压测目标很关键：

| 目标 | 方法 | 测到的是 | 注意 |
| --- | --- | --- | --- |
| **经 SSH 隧道直连应用**（测容量推荐） | `ssh -N -L 18000:127.0.0.1:8000 mcs21-vps`，然后 `--base-url http://127.0.0.1:18000/api/v1` | 应用和数据库本身，不经过 nginx 和 TLS | 大文件吞吐受压测机自己的上行带宽限制，报告里要写明 |
| 入口（公网地址） | `--base-url https://secureview.tech/api/v1` | 包含 nginx 和 TLS 的真实路径 | 从一台机器主要测到每秒 10 个请求的限制；适合*展示*限流，不适合测容量 |
| 在另一台服务器上压测（如 j1900） | 从那台机器开同样的隧道 | 与直连相同，带宽取决于那台机器 | 需要在那台机器上装 loadtest 环境 |

在 VPS 本机上跑压测工具虽然没有网络瓶颈，但会抢占被测服务器的 CPU，所以不推荐。

## 测试矩阵

对应会议纪要里的矩阵。时长只是建议；错误率超过约 5% 或 p95 涨到三倍以上时，就不要再继续加压。

| 维度 | 命令（接在通用参数之后） | 记录 |
| --- | --- | --- |
| 并发用户 | `steps --users 1,5,10,20,50,100 --duration 60 --size 1MiB` | 每档的 p50/p95/p99、每秒操作数、错误 |
| 文件大小与类型 | `sizes --sizes 1MiB,10MiB,50MiB,100MiB,200MiB,500MiB --types pdf,png,jpg,mp4,zip,exe` | 每个文件：上传、下载、分享、接收方下载、客户端加解密耗时、SHA-256 是否一致 |
| 单用户并行任务 | `parallel --users 5 --tasks 1,2,5,10 --duration 60` | 一个用户会不会拖慢其他人 |
| 混合负载 | `mixed --users <稳定值> --duration 300`（70% 上传、20% 下载、10% 分享/列表） | 最接近真实使用 |
| 持续压力 | `mixed --users <接近上限> --duration 1800 --window 60`（15/30/60 分钟） | p95、内存、连接数随时间的变化 |
| 超载与恢复 | `steps --users <稳定值>,<稳定值×1.5>,<稳定值×2>,<稳定值> --duration 60` | 超载时的错误类型，以及最后一档能否恢复 |
| 同时登录 | `logins --users 1,2,4,8,16 --rounds 3` | Argon2id 并发上限和登录死锁率，不重试 |

整个测试期间在服务器上运行 `server_sampler.py`；报告会把它记录的 CPU、iowait、内存、磁盘、网络、API 与 MySQL 进程的 CPU/内存，
以及数据库连接数，按每一档的时间段对齐。

## 运行步骤

**前提：** 服务器上没有别的负载；已通知团队；在 04:15 备份之前结束（否则备份会把测试文件也复制进去），也要在 05:30 完整性扫描之前结束。

1. 在服务器上创建测试账号（文件权限 0600，只含测试账号）：

   ```bash
   cd /opt/mcs21/current/backend && set -a && . /etc/fyp-secure-file-platform/backend.env && set +a
   sudo -u fypapp env PYTHONPATH=$PWD .venv/bin/python scripts/seed_load_users.py \
     --count 100 --out /tmp/loadtest-accounts.json
   ```

   把文件复制到压测机（`scp mcs21-vps:/tmp/loadtest-accounts.json .`），然后从服务器上删掉。
2. 在服务器上启动采样：
   `python3 /opt/mcs21/current/loadtest/server_sampler.py --interval 2 --out /root/loadtest-metrics.csv`
3. 在压测机上开隧道并运行各场景：

   ```bash
   cd loadtest && uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python -r requirements.txt
   ssh -N -L 18000:127.0.0.1:8000 mcs21-vps &
   .venv/bin/python -m secureview_load --base-url http://127.0.0.1:18000/api/v1 \
     --accounts loadtest-accounts.json --confirm-remote --out results steps --users 1,5,10,20,50,100
   ```

   目标不是本机时，没有 `--confirm-remote` 工具会拒绝运行。
4. 停止采样（Ctrl-C），把 CSV 复制回来，生成报告：
   `.venv/bin/python -m secureview_load.report results --server-metrics loadtest-metrics.csv --out results/REPORT.md`
5. 通过 API 删除测试账号及其全部文件：
   `.venv/bin/python -m secureview_load --base-url … --accounts loadtest-accounts.json --confirm-remote cleanup`

**存储：** 每次上传 1 MiB 时，一档 100 用户的测试就可能写入好几 GiB。清理会删掉它们；前后各看一次 `df -h`。

## 本地预演

`loadtest/run_local.sh` 用小规模参数对一次性的本地 API 和 MySQL（数据库名必须包含 `_test`）跑完所有场景，生成报告，并删除测试账号。
它的数字描述的是笔记本而不是服务器；它的作用是让正式测试不出意外。

```bash
DB_HOST=127.0.0.1 DB_PORT=3310 DB_USER=root DB_PASSWORD=... DB_NAME=fyp_loadtest_test bash loadtest/run_local.sh
```

工具自身的测试：`cd loadtest && .venv/bin/python -m pytest tests`。

## 正式测试必须得出的结论

来自会议纪要，等 staging 报告出来后填写：

- **容量：** “在当前服务器（8 vCPU、16 GB）上，系统可稳定支持 ___ 个并发用户，每用户 ___ 个并行文件任务；在 ___ MB 文件规模下
  p95 为 ___ 秒，错误率 ___%。”
- **瓶颈：** “并发超过 ___ 后，主要瓶颈出现在 ___（CPU / 内存 / 磁盘 / 网络 / 数据库 / 单个 API 进程），因此扩展方式是 ___
  （增加 worker、扩大连接池、限流）。”
- **大文件：** “所有类型在 ___ MB 以内都能逐字节一致地往返（SHA-256 验证）；500 MB 在 ___ Mbit/s 的链路上上传 ___ 秒、下载 ___ 秒。”
- **登录：** “服务器按设计同一时间只验证两个密码；___ 个同时登录中有 ___% 被拒绝并需要重试。”
