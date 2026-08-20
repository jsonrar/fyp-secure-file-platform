# MySQL 部署

[English](DEPLOYMENT.md) | [简体中文](DEPLOYMENT.zh-CN.md)

本文说明如何把数据库部署到 MySQL 8.4。生产及预发布环境只接受经过评审的 SQL；这些环境
不安装、不调用 Alembic，也不创建 `fyp_migrator`。SQLAlchemy metadata 和
Alembic revision 仍用于开发与 CI 中编写、评审及验证 Schema；生产交付物是与当前 head
保持一致的 `database/mysql/02-schema.sql`。

生产首次部署使用以下顺序：

1. 数据库管理员以 root/管理员身份执行 `database/mysql/01-provision.sql`。
2. 同一管理员执行 `database/mysql/02-schema.sql`；该文件只允许用于空应用数据库。
3. 同一管理员执行只读的 `database/mysql/03-verify.sql` 并评审全部结果。
4. 只有核验通过后，应用才以 `fyp_user` 启动。

三个步骤必须分别在 MySQL 客户端的遇错停止 batch 模式下成功。不要使用交互式 `SOURCE`，
不要添加 `--force`，也不要在某一步失败后继续下一步。

## 身份、配置与 Secret

生产只使用两个身份：

- MySQL root/管理员创建数据库和运行时账户、创建 Schema、授予权限并执行最终核验。管理员
  凭据不得写入应用 `.env`、命令参数、Git、日志或工单。
- `fyp_user` 是唯一应用身份。应用通过标准 `DB_USER`/`DB_PASSWORD` 注入其凭据，绝不能
  获得管理员凭据。

应用继续使用以下标准设置：

- `DB_HOST`、`DB_PORT`、`DB_NAME`（所提供 SQL 固定使用
  `fyp_secure_file_platform`）、`DB_USER` 和 `DB_PASSWORD`；
- `DB_SSL_CA`，用于验证服务器证书和 `DB_HOST`；
- 需要双向 TLS 时，同时提供 `DB_SSL_CERT` 和 `DB_SSL_KEY`。

`fyp_user` 带有 `REQUIRE SSL`。非开发环境必须验证服务器证书；CA/client 文件应作为只读
部署 secret 挂载。管理员远程连接同样应使用 `--ssl-mode=VERIFY_IDENTITY` 和受信任 CA。
非开发环境还必须设置 `APP_DEBUG=false`、不少于 32 个字符的非默认 `SECRET_KEY`，并明确
列出允许的 CORS origin。

`MYSQL_ROOT_PASSWORD` 和 `MYSQL_PORT` 仅供根目录 Compose 本地开发使用，不是生产管理员
配置。生产不使用任何部署专用的管理员、迁移或账户 Host 环境变量。

## `localhost` 与远程账户来源

仓库中的三份 SQL 默认使用 ``'fyp_user'@'localhost'``，适用于应用从数据库主机连接的
部署。MySQL 账户中的 Host 表示客户端连接来源，并不是 `DB_HOST` 的值。

若应用远程连接，请在仓库外为三份 SQL 各制作一份受保护、经评审的部署副本，并在三份
副本中一致替换每一个 `localhost` 账户 Host：

- `01-provision.sql` 中的账户创建目标；
- `02-schema.sql` 中的表级及列级授权目标；
- `03-verify.sql` 中的账户与授权期望。

使用部署网络允许的最窄固定主机或模式。不要提交环境专用副本，也不要无条件使用 `%`；
即使网络和防火墙另有限制，数据库账户本身也应限制来源。

## 1. 管理员执行 Provision

在数据库服务器的仓库根目录中，如果 MySQL root 使用本机 socket 认证，执行：

```bash
sudo mysql < database/mysql/01-provision.sql
```

如果 root 使用密码认证，让客户端交互提示密码，不要把密码写进命令：

```bash
mysql --user=root --password < database/mysql/01-provision.sql
```

远程管理员连接使用受保护的环境副本并验证 TLS：

```bash
mysql --host=<mysql-host> --port=3306 --user=<administrator> --password \
  --ssl-mode=VERIFY_IDENTITY --ssl-ca=/path/to/mysql-ca.pem \
  < /protected/path/01-provision.sql
```

`01-provision.sql` 创建固定名称、`utf8mb4`/`utf8mb4_unicode_ci` 的数据库，并创建带
`REQUIRE SSL` 的 `fyp_user`。MySQL 为新账户生成随机密码并在客户端结果集中返回。管理员
必须在不会记录会话输出的受控终端中立即把该明文保存到 secret store；MySQL 之后无法还原
它。禁止截图、复制到聊天或工单，或写入持久化应用 `.env`。

该文件不创建应用表，也不授予尚不存在表上的运行时权限。表和精确表/列级授权由下一步统一
创建，避免给 `fyp_user` Schema 级 DML 或任何 DDL 权限。

脚本使用 `CREATE USER IF NOT EXISTS`：重复执行不会修改已有账户的密码、认证插件或 TLS
策略。已有同名账户必须评审 `SHOW WARNINGS` 及最终核验结果；不要把重复运行 Provision
当作凭据轮换或权限修复。凭据轮换和额外账户清理都必须作为单独、经过协调的运维变更。

## 2. 管理员创建空库 Schema 与最小授权

`02-schema.sql` 是当前生产 Schema 的完整快照，只能用于不含任何应用表和迁移 metadata 的
空数据库。它不是已有数据库的升级脚本。执行前确认目标名称无误，并确认没有需要保留的
数据：

```bash
sudo mysql < database/mysql/02-schema.sql
# root 使用密码认证时：
mysql --user=root --password < database/mysql/02-schema.sql
```

远程执行时使用三份受保护副本中的第二份：

```bash
mysql --host=<mysql-host> --port=3306 --user=<administrator> --password \
  --ssl-mode=VERIFY_IDENTITY --ssl-ca=/path/to/mysql-ca.pem \
  < /protected/path/02-schema.sql
```

该文件负责：

- 在外键依赖允许的顺序中创建当前 head 的 15 张应用表、索引、约束和 Schema 版本标记；
- 创建单例 `audit_chain_heads.id = 1` 初始行；
- 在表已经存在后，只向 `fyp_user` 授予 13 张普通状态表所需的精确 CRUD、
  `audit_logs` 的 `SELECT`/`INSERT`、`audit_chain_heads` 的表级 `SELECT`，以及仅限
  `last_log_id`、`current_hash`、`updated_at` 三列的 `UPDATE`；运行时账户不能更新
  `schema_revision`；
- 不授予 Schema 级、全局、DDL、`GRANT OPTION`、role 或 proxy 权限。

chain-head 列默认值和初始行都先使用最后一个已完成 revision。运行时授权和
`alembic_version` 标记成功后，脚本先把列默认值恢复为最终 0003 Schema 值，再由最后一条语句
显式发布 singleton 的 `0004_email_verification_codes`。因此部分完成的安装不能通过 readiness，完整
安装后的 Schema 又与 ORM 和 Alembic head 等价。

空库保护失败、任何对象已存在或任何 DDL 报错时，必须立即停止。MySQL DDL 可能部分提交；
失败后不得加入 `IF NOT EXISTS`、不得覆盖或盲目重跑脚本。应保持应用停止、保留现场供诊断，
并从已验证备份恢复；若这是全新的无数据目标，也只能在确认完整清理范围后重新创建空库。

生产环境不运行 `alembic upgrade`、`alembic current`、`alembic check` 或
`alembic stamp`。`alembic_version` 若作为快照中的 Schema 标记存在，只表示该快照与哪个
开发/CI head 对齐，不表示生产曾执行 Alembic。

## 3. 管理员执行只读核验

只有前两份 SQL 都成功后，执行：

```bash
sudo mysql < database/mysql/03-verify.sql
# root 使用密码认证时：
mysql --user=root --password < database/mysql/03-verify.sql
```

远程部署使用包含同一窄 Host 的第三份受保护副本：

```bash
mysql --host=<mysql-host> --port=3306 --user=<administrator> --password \
  --ssl-mode=VERIFY_IDENTITY --ssl-ca=/path/to/mysql-ca.pem \
  < /protected/path/03-verify.sql
```

操作员必须逐项确认：

- 服务器为 MySQL 8.4、严格 SQL mode 已启用、Session 时区符合部署预期，数据库字符集和
  排序规则正确；
- `fyp_user` 只有一个预期 Host 行，凭据、认证插件、锁定/过期状态和 TLS 要求符合预期；
- 不存在任何 Host 的旧 `fyp_migrator` 账户；
- `fyp_user` 没有全局或 Schema 级权限，只有 `02-schema.sql` 定义的精确表/列级权限，且
  `IS_GRANTABLE=NO`；
- 表级权限差集为空；列级权限差集也为空，且只包含
  `audit_chain_heads.last_log_id/current_hash/updated_at` 的 `UPDATE`，绝不包含
  `schema_revision`；routine、role、default-role 和 proxy 结果为空，服务器没有会向应用
  账户附加权限的 mandatory role；
- 应用表集合、关键 Schema metadata、版本标记及约束符合当前快照；
- `alembic_version` 恰好为 `0004_email_verification_codes`；
- `audit_chain_heads` 恰好包含一个 `id = 1`、空 `last_log_id`、64 个零哈希且
  `schema_revision = '0004_email_verification_codes'` 的单例行。

任何 `REVIEW`、缺失项、多余账户或多余权限都必须阻止应用启动。核验 SQL 只读取状态，不会
自动修复账户、权限或 Schema。

## 4. 退役旧 `fyp_migrator` 并启动应用

从旧流程升级运维规范时，可能仍存在一个或多个 `fyp_migrator@Host`。先确认没有发布 Job、
定时任务或外部服务仍依赖它，记录其所有 Host 和 grant，再由管理员显式撤权并 `DROP USER`。
不要让 Provision 自动删除来源不明的账户。必须重复运行 `03-verify.sql`，直到所有旧 migrator
行都消失且其权限不再存在。

核验完全通过后，只向应用进程注入 `fyp_user` 的标准 `DB_*` 和 TLS secret，再启动新版本。
应用不得持有 root/管理员凭据，也不得获得 DDL 或账户管理权限。

启动后，实例加入服务前必须同时通过 `GET /health/live` 与 `GET /health/ready`。
Readiness 会探测数据库并要求精确 Schema revision `0004_email_verification_codes`；它只诊断漂移，
不会执行 migration 或 stamp。

## 5. 在 nginx 终止 TLS

预发布 VPS 通过 Let's Encrypt 证书以 HTTPS 提供 `secureview.tech`。线上 server 块的版本化副本
位于 `deployment/server/nginx-secureview.conf`。

```bash
sudo apt-get install -y certbot python3-certbot-nginx
sudo certbot --nginx -d secureview.tech -d www.secureview.tech --redirect
```

`certbot --nginx` 会重写 80 端口块，因此任何改动过配置的续期之后，都必须重新应用下面的回环
探针例外，并与版本化副本比对。

这里的 HTTPS 不是装饰。浏览器只在安全上下文中暴露 `crypto.subtle`，而注册流程依赖它生成账户
RSA 密钥对并派生 Argon2id KEK。在明文 HTTP 下客户端登记代码根本拿不到该 API，注册无法完成。

### 80 端口块与发布探针

`mcs21-deploy` 会带 `Host: <public_host>`（即服务器裸 IP）探测
`http://127.0.0.1/health/live` 与 `http://127.0.0.1/`。certbot 生成的跳转只匹配两个域名，
其余一律返回 `404`，会导致部署后的存活检查失败并回滚发布。

因此 80 端口块保留且仅保留这两个路径，并限制为回环访问：

```nginx
location = /health/live {
    allow 127.0.0.1;
    allow ::1;
    deny all;
    proxy_pass http://127.0.0.1:8000;
    include /etc/nginx/proxy_params;
}

location = / {
    allow 127.0.0.1;
    allow ::1;
    deny all;
    error_page 403 = @canonical;
    try_files /index.html =404;
}

location @canonical {
    return 308 https://secureview.tech$request_uri;
}

location / {
    return 308 https://secureview.tech$request_uri;
}
```

回环访问两个探针仍然得到 `200`。80 端口上的其余请求一律跳转到规范的 HTTPS 源，裸 IP 也不例
外——`error_page` 把访问阶段的 `403` 转成同一个跳转。两种情况下都不会有任何内容以明文送出。

跳转用的是 `308` 而非 `301`，这样对 `/api/` 的 `POST` 会保留方法与请求体，而不会变成 `GET`
再以 `405` 失败。

### 用 IP 访问这台机器

443 端口块的 `server_name` 里带了裸 IP，所以 `https://103.233.0.105/` 确实能打开站点；但
Let's Encrypt 证书只覆盖 `secureview.tech` 与 `www.secureview.tech`，浏览器会给出证书名称不
匹配的警告。Let's Encrypt 不为 IP 地址签发证书——IP 没有可供校验的名称。

请统一使用 `https://secureview.tech`。`http://103.233.0.105/<路径>` 会跳转过去，这才是受支持
的入口：例如直接输入 IP 访问 API 文档，会落到 `https://secureview.tech/docs`。

在这个跳转存在之前，以 HTTP 访问裸 IP 时，除两个回环探针外的所有路径都由 nginx 返回 `404`。
那个页面很容易被读成"后端挂了"，而实际上只是明文请求找不到可跳转的名称而被拒绝。

### 首次访问的 HTTP 跳转

`.tech` 不在浏览器 HSTS 预加载名单中，因此不带协议直接输入 `secureview.tech` 的访客会先经过
一次 `http://` 才被跳转。此后 `Strict-Transport-Security` 头会将 HTTPS 固定一年。对外发布与
分享链接时请一律写作 `https://secureview.tech`，即可完全避免这一跳——部分应用内置浏览器会
在该跳转期间提示不安全。

## 后续非空生产数据库升级

不得在非空生产数据库上重跑 `02-schema.sql`，也不得运行 Alembic。每次 Schema 变化必须提供
独立、按版本命名、经过 DBA 评审的前向 SQL，并明确：

1. 唯一允许的前置 Schema 版本和完整预检；
2. 停止/排空写入以及同一数据库只允许一个升级执行者；
3. 已验证可恢复的加密备份、整体期限和有限 metadata-lock 等待；
4. DDL 执行顺序、数据回填、发布后核验以及部分提交时的恢复步骤；
5. 成功后更新 Schema 版本标记，并运行当前 `03-verify.sql` 或该升级配套的核验 SQL。

Alembic revision 可继续在开发/CI 中表达同一变化，但生产 DBA SQL 必须单独评审，且 CI 必须
证明它产生的最终 Schema 与当前 Alembic head/ORM metadata 等价。

备份必须在仓库外加密保存、限制访问并定期演练恢复。数据库 dump 包含登录密码哈希、公开
Argon2id 参数、已包装 AMK、客户端加密私钥包、安全审计证据、明文运营文件 metadata 及包装
文件密钥。它们不是明文私钥或 DEK，但仍能用于离线猜测 passphrase，并暴露所有权/共享关系，
因此必须作为高度敏感数据保护。

## Compose、本地开发与历史 `init.sql`

根目录 `docker-compose.yml` 只用于本地开发。MySQL 官方镜像会在全新 volume 上根据
`MYSQL_ROOT_PASSWORD`、`DB_NAME`、`DB_USER` 和 `DB_PASSWORD` 创建数据库及开发账户；
开发者可在该一次性环境中运行 Alembic。这不等同于生产表级权限，也不会自动执行三份生产
SQL。已有 volume 不会因为环境变量变化而重新初始化。

不要在普通 Compose 开发 volume 上随意执行生产 Provision/Schema SQL。同名开发账户可能
已有更宽权限，已有表也应触发空库保护。三份生产 SQL 和 Alembic revision 都不应挂载到
`/docker-entrypoint-initdb.d`；官方镜像只在全新 volume 初始化时执行该目录，无法承担持续
版本升级。

历史版本曾包含 `docs/init.sql`。它不是当前 Schema 来源，现已从部署流程移除。由它创建的
非空、无已知版本标记数据库仍属于未受管理旧数据库，不能运行 `02-schema.sql`，也不能在
生产环境运行 Alembic；应按[数据库接管策略](DATABASE_SCHEMA.zh-CN.md)重建，或使用单独、
经评审的 DBA 接管 SQL。
