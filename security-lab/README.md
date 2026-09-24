# Isolated VPS tamper drill / 隔离 VPS 篡改演练

This lab is the project-owned “attacker machine” for Issue #90. It runs on the same VPS but
has a separate internal-only Docker network, MySQL 8.4 database, and encrypted-object volumes.
It never mounts the Docker socket, host network, production environment, production database,
or production object directories. Both application containers drop every Linux capability,
use a read-only root filesystem, and have CPU, memory, process, and temporary-storage limits.

这是 Issue #90 的项目自有“攻击机”。它与 SecureView 运行在同一台 VPS 上，但使用独立的内部
Docker 网络、MySQL 8.4 数据库和密文卷；不会挂载 Docker socket、宿主机网络、生产环境变量、
生产数据库或生产密文目录。两个应用容器均丢弃全部 Linux capability，根文件系统只读，并限制
CPU、内存、进程数和临时存储。

## Run / 运行

```bash
bash security-lab/run.sh
```

The runner generates disposable credentials, migrates the `_test` database, creates a synthetic
encrypted fixture through the real `FileService`, launches the attacker for each mutation, and
destroys every container, network, credential file, and named volume on exit. Sanitized reports
are written under `security-lab/reports/` and are ignored by Git.

脚本会生成一次性凭据、迁移 `_test` 数据库、通过真实 `FileService` 创建合成加密测试文件，
随后逐项启动攻击容器；退出时会销毁本次容器、网络、凭据文件和命名卷。脱敏报告写入
`security-lab/reports/`，且不会被 Git 跟踪。

## What it proves / 证明内容

1. Baseline ciphertext is `VALID`, has durable status `ACTIVE`, and can be downloaded.
2. Flipping one ciphertext byte returns `MODIFIED`, persists `CORRUPTED`, and refuses download.
3. Restoring the original bytes returns `VALID` and heals the durable status to `ACTIVE`.
4. Temporarily removing an object returns `MISSING` without permanently changing its status.
5. If an attacker controls both storage and the database, they can replace the recorded digest
   and make the server-side SHA-256 comparison pass. The original AEAD tag still rejects the
   modified ciphertext on the client. SHA-256 is therefore a useful detector, not a trusted root
   after simultaneous database-and-storage compromise.

1. 基线密文显示 `VALID`、持久状态为 `ACTIVE`，并且可下载。
2. 翻转一个密文字节后显示 `MODIFIED`、持久状态变为 `CORRUPTED`，下载被拒绝。
3. 恢复原始密文后重新显示 `VALID`，持久状态恢复为 `ACTIVE`。
4. 临时移走对象时显示 `MISSING`，不会永久改变文件状态。
5. 如果攻击者同时控制存储和数据库，就能替换记录中的摘要，使服务端 SHA-256 比较通过；但
   原来的 AEAD 认证标签仍会让客户端拒绝被修改的密文。因此 SHA-256 是有效检测器，却不能在
   数据库与对象存储同时失陷后继续充当可信根。

Do not point this lab at another system, change its database name to a non-test name, or add any
production mount. Both Python entry points independently refuse those conditions.

不要把实验指向其他系统，不要把数据库名改成非测试名称，也不要添加任何生产挂载；两个 Python
入口都会分别拒绝这些条件。
