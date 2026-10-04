# 现场篡改演示

[English](TAMPER_DEMO.md)

4 分钟演示里的大约 40 秒：当着观众的面改掉服务器上存储的密文，然后展示接收方下载时被拒绝。
它回答的是“你说加密了、校验了，证明给我看”，而且是观众亲眼看到发生的。

工具是 [`backend/scripts/demo_tamper.py`](../../backend/scripts/demo_tamper.py)。它只会动用户名以
`demo-` 开头的账号拥有的文件；指定的账号不是文件所有者就拒绝；`restore` 之前一直保留原始字节和
数据库里的原值；没有 `restore` 就不允许第二次篡改。

## 演示内容

| 命令 | 对服务器做了什么 | 观众看到什么 | 被哪道检查拦下 |
| --- | --- | --- | --- |
| `flip` | 把存储的密文正中间改掉一个字节 | 下载被拒，提示“The encrypted file could not be verified”（加密文件无法通过校验）；这一行变成 **Modified（已改动）** | 服务器在发送文件前先算哈希，和数据库里记录的 SHA-256 比对 |
| `forge` | 改掉一个字节，**同时**把数据库里记录的摘要和大小改成与之一致，相当于攻击者同时拿到了存储和数据库的写权限 | 同样被拒 | 上传时写进哈希链审计日志的摘要，与被改过的那一列对不上 |
| `restore` | 把原始字节、摘要、大小和状态全部还原 | 又能正常下载 | — |
| `list` | 不做任何修改，只列出该账号的文件和 id | — | — |

第三道防线是浏览器里的 AES-GCM 认证标签：即使攻击者绕过了服务器的两道检查，它也能发现。要现场
展示这一层，就得在 staging 上改写审计链，所以这一层交给 `frontend/src/crypto/download.test.ts`
和 CI 里的 `tamper-drill` 来证明；评委问到时这样说明即可。

## 展示前（做一次）

1. 在 staging 上准备两个演示账号（例如 `demo-alice` 和 `demo-bob`；**账号由用户来注册**，助手不在
   线上站点替人注册）。
2. 用 `demo-alice` 上传一个小的、能直接看懂的文件（例如 `quarterly-results.txt`），分享给
   `demo-bob`。再用 `demo-bob` 下载一次，确认能打开。
3. 在服务器上查文件 id（用下面的命令，把 `flip` 换成 `list`，去掉 `--file-id`）。它会列出该账号的
   每个文件和 id，并标出还处于篡改状态的文件。
4. 把下面整套流程完整预演一遍，最后一定要 `restore`。

## 演示时

提前准备两个窗口：浏览器以 `demo-bob` 登录，停在 My Files → Shared with me（与我共享）；终端已经
连上服务器。

提前在终端里执行好下面两条，然后放着：

```bash
ssh mcs21-vps
```

```bash
cd /opt/mcs21/current/backend && set -a && . /etc/fyp-secure-file-platform/backend.env && set +a
```

当着观众执行：

```bash
sudo -u fypapp --preserve-env=DB_HOST,DB_PORT,DB_NAME,DB_USER,DB_PASSWORD,DB_SSL_CA,ENCRYPTED_FILE_DIR PYTHONPATH=$PWD .venv/bin/python scripts/demo_tamper.py flip --owner demo-alice --file-id <id>
```

可以这样说：“假设我是服务器管理员，或者是入侵了服务器的人。我刚刚把 Alice 这个文件在磁盘上改了
一个字节。”切到浏览器，以 `demo-bob` 点下载。下载被拒绝，这一行显示 **Modified**。

时间够的话可以加演：先 `restore`，再用同样的方式执行 `forge`，然后再下载一次。可以这样说：“这次
我连数据库也一起改，让记录的摘要和文件对得上。还是被拒绝，因为上传时这个摘要也写进了防篡改的
审计链。”

最后一定要执行：

```bash
sudo -u fypapp --preserve-env=DB_HOST,DB_PORT,DB_NAME,DB_USER,DB_PASSWORD,DB_SSL_CA,ENCRYPTED_FILE_DIR PYTHONPATH=$PWD .venv/bin/python scripts/demo_tamper.py restore --owner demo-alice --file-id <id>
```

然后以 `demo-alice` 登录，在 My Files 里点一下这个文件的 **Modified** 状态标签。这会重新做一次
完整性检查，标签会变回 **Verified（已验证）**。

## 注意事项

- 备份保存在 `/var/lib/fyp-secure-file-platform/demo-tamper/`（权限 0600，属主 `fypapp`），
  `restore` 后自动删除。演示中途终端断开也没关系，之后再执行 `restore` 照样能还原。
- 如果文件一直处于篡改状态，夜间完整性巡检和安全 Agent 会报告它，并可能发告警邮件。演示完马上
  还原。如果讲的过程中真的收到告警，正好说明监控在工作。用 `list` 可以查看还有没有没还原的文件。
- 两种篡改的报错文字一样，这是有意设计的：服务器只告诉客户端“存储的副本没通过检查”，不说是哪一道
  检查没通过。

## 已验证

本地 MySQL 8.4 + 真实前端（2026-10-04）：`flip` → 下载被拒，提示“The encrypted file could not
be verified”，这一行显示 Modified；`restore` → 下载解密出原文；`forge` → 被审计链锚点拦下；
`restore` → 又能正常下载；点状态标签后这一行变回 Verified；`list` 列出了文件和 id。拒绝情况也已
验证：账号名不以 `demo-` 开头、指定账号不是文件所有者、没 `restore` 就再次 `flip`、`flip` 不带
`--file-id`。
