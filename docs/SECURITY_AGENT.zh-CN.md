# 安全 Agent

[English](SECURITY_AGENT.md) | [简体中文](SECURITY_AGENT.zh-CN.md)

导师对 AI Agent 一项的要求是：Agent 要**解决明确的自动化问题，而不是单纯加聊天框**——定义它的输入数据、
规则或模型、输出格式与边界，并演示 Critical / High / Medium / Low 分类及 Recommended Action。
本文就是这一定义，以及已实现的内容（管理员页面 → **Security agent**）。

## 它自动化的问题

平台已经记录了很多东西：哈希链审计日志、完整性检查、文件状态、恢复请求。没有哪位管理员会去读几千行记录，
来发现某个账户正被猜密码、某个会话令牌被重复使用、或某个存储文件被改动。Agent 替他们读这些证据，回答一个问题：
**在发生的所有事情里，现在哪些值得我关注，有多紧急，我该做什么？**

## 它是什么，不是什么

| 它是 | 它不是 |
|---|---|
| **基于规则、确定性的。** 每个发现都来自一条有名字、有明确阈值的规则。相同证据得到相同报告，每条规则都用伪造事件做单元测试，管理员能读到某件事为何被标记。 | 让语言模型去判断日志。没有任何模型被询问，所以不会猜测，也没有日志离开服务器。 |
| **只读。** 它从不写入，不改文件或账户，也不能执行恢复。有测试保证它的模块一旦出现数据库写入或审计追加就失败。 | 被允许“修复”问题。它只建议，由管理员执行。 |
| **只用元数据。** 只读取事件类型、时间、次数、账户名、来源地址和文件标识。 | 能看到文件内容、密钥、口令或密文。查询只选取指定的列，并有测试固定这一点。 |
| **坦承自己的局限。** 每份报告都说明读了多少数据，结果为空时也会说明这不等于什么都没发生。 | 声称一切安全。它只能看到平台记录下来的东西。 |

## 输入数据

| 来源 | 读取内容 |
|---|---|
| `audit_logs`（窗口：最近 24 小时或 7 天） | `AUTH_LOGIN_FAILED`、`AUTH_REFRESH_REPLAY_DETECTED`、`FILE_DOWNLOAD_AUTHORIZED`、`FILE_SHARED`、`AUTH_PASSWORD_CHANGE_FAILED`、`RECOVERY_REQUEST_EXECUTED`：动作、时间、账户名、来源地址 |
| 审计哈希链 | 完整重算（`AuditQueryService.verify_chain`）：是否有效，以及第一个失败的条目 |
| `integrity_checks` 与 `files` | 状态为 `CORRUPTED`，或最新检查为 `MODIFIED`、`MISSING`、`ERROR` 的文件，以及每个文件的检查历史 |
| `recovery_requests` | 超过 24 小时仍待处理的数量 |
| 完整性扫描的覆盖情况 | 最近一次扫描的时间、从未检查过的文件数 |

## 规则

| 规则 | 观察对象 | 触发 |
|---|---|---|
| `INTEGRITY_DAMAGE` | 受损的存储文件 | **MODIFIED = Critical**，MISSING = High，ERROR = Medium |
| `AUDIT_CHAIN_BROKEN` | 审计哈希链 | 任一条目验证失败 = **Critical** |
| `SCAN_NOT_RUNNING` | 最近一次完整性扫描 | 有文件时 36 小时内（或从未）没有扫描 = Medium |
| `LOGIN_GUESSING_SOURCE` | 每个来源地址的登录失败 | 15 分钟内 10 次以上 = Medium，30 次以上 = High |
| `LOGIN_GUESSING_ACCOUNT` | 每个被攻击账户的登录失败 | 15 分钟内 10 次以上 = Medium |
| `SESSION_TOKEN_REUSE` | 已使用过的刷新令牌再次出现 | 任意一次 = High |
| `DOWNLOAD_BURST` | 每个账户的下载 | 10 分钟内 20 次以上 = Medium，60 次以上 = High |
| `SHARE_BURST` | 每个账户的分享 | 一小时内 10 次以上 = Low |
| `PASSWORD_CHANGE_GUESSING` | 每个账户的改密失败 | 15 分钟内 5 次以上 = Medium |
| `RECOVERY_EXECUTED` | 已执行的恢复、等待超过一天的请求 | 已执行 = Medium，等待 = Low |

突发用滑动窗口衡量：一天里分散的 40 次失败不算突发；五分钟内的 10 次才算。阈值是
`backend/app/services/security_agent_rules.py` 顶部的常量，修改需要经过代码评审，报告里也会写明。

优先级含义：**Critical** 立即处理，**High** 今天处理，**Medium** 本周查看，**Low** 方便时处理。

## 输出格式

`GET /api/v1/admin/agent/report?window_hours=24|168`（仅管理员）返回、页面展示：

```
generated_at, window_hours
counts:      critical / high / medium / low
findings[]:  rule_id, priority, title, summary,
             evidence[]            （为何被标记：次数、账户、地址、时间）,
             recommended_action    （该做什么）,
             file_id?              （文件类发现）
rules[]:     每条规则、它观察什么、阈值、这次触发了几个发现
inputs:      读取的审计事件数、验证的审计链条目数、可检查/从未检查的文件数、最近一次扫描
boundaries[] Agent 不会做的事
```

## 受损文件的恢复指引

对受损文件，建议动作会给出确切的命令（`scripts/restore_file.py --file-id …`，始终是演练模式），并**根据该文件自己的检查历史
推算哪些备份集可能持有原件**：在上传与最后一次通过检查之间生成的备份集*一定*持有；到首次发现损坏为止的备份集*很可能*持有；
更晚的备份集可能已经含有被损坏的字节。`restore_file.py` 会校验 SHA-256 并拒绝不匹配的备份集。这样 Agent 与
[BACKUP_AND_RECOVERY.zh-CN.md 第 9 节](BACKUP_AND_RECOVERY.zh-CN.md) 的恢复流程衔接起来，却不能自己去执行它。

## 演示（用真实事件，不伪造任何东西）

审计日志只能追加且带哈希链，无法注入假事件，也不需要。展示各个级别的方法：

1. **Medium，猜密码：** 对同一账户发送十次错误密码。登录限流在十次之后返回 429，这十次都在审计日志里，
   报告就会显示 `LOGIN_GUESSING_SOURCE` 和 `LOGIN_GUESSING_ACCOUNT`。
2. **Critical，文件被篡改：** 在篡改实验室（`security-lab/run.sh`）或一次性环境中翻转一个存储对象的字节，
   在 Integrity 标签点 **Scan now**，再打开 **Security agent**：显示 `INTEGRITY_DAMAGE`、备份窗口和恢复命令。
3. **High，对象丢失：** 把一个对象移出存储后扫描：`INTEGRITY_DAMAGE` 为 High，描述为存储问题而非篡改。
4. **Medium，检测未运行：** 在定时器已 36 小时没有运行的部署上。

## 测试

- `tests/unit/test_security_agent_rules.py`：每条规则的阈值、分级、对正确来源与账户的归因、排序、确定性、
  备份窗口文字，以及只会建议演练模式。
- `tests/unit/test_security_agent_service.py`：窗口、请求了哪些事件、检查历史如何变成“最后一次完好”与“首次发现损坏”、
  仅管理员可用、SQL 只选取指定列，以及模块没有写入路径。
- `tests/integration/test_security_agent_mysql.py`：在真实 MySQL 上，真正被篡改的文件被报告为 Critical 并给出备份窗口，
  所有查询都能运行。
- `frontend/src/utils/agent-report.test.ts`：发现如何展示。

## 局限与下一步

- 它只能看到被记录下来的内容。没有留下审计事件的攻击对它不可见。
- 代理之后的来源地址，只和 API 所信任的代理头一样可靠。
- 没有报告历史，也没有通知：被询问时才回答。自然的下一步是每天运行，并把 Critical/High 发现通过现有的失败告警邮件发出。
- **v1 有意不包含语言模型层。** 它唯一合理的用途是为非技术读者改写发现的措辞，而这会把审计元数据（账户名、地址）
  发给第三方。若以后要加，应当是可选、默认关闭，只接收已脱敏的发现文字，且绝不允许它改变优先级或执行动作。
