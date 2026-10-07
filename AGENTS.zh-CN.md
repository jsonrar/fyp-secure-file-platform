# 仓库 Agent 规则

[English](AGENTS.md) | 简体中文

> 本文是 `AGENTS.md` 的中文版，供组员阅读；自动化工具读取的是英文版，两者内容须保持一致。

这些规则适用于整个仓库。

## 应用层 HTTP 方法

- 应用层 HTTP 端点、客户端、测试、示例和 OpenAPI 契约只能使用 `GET` 和 `POST`。
- 基础设施仍可处理浏览器和 HTTP 服务器要求的协议层行为（例如自动的 CORS 预检），但应用代码不得把这些方法
  定义或发起为业务 API 操作。
- `GET` 只用于只读操作。创建、更新、删除、撤销以及其他所有改变状态的命令或动作都用 `POST`。
- 必要时，改变状态的动作路由使用明确的动作路径，例如 `POST /files/{file_id}/delete` 和
  `POST /auth/sessions/{session_id}/revoke`。
- 不得新增或保留应用层的 HTTP `PUT`、`PATCH` 或 `DELETE` 路由及客户端调用。
- CORS 的 `allow_methods` 只能包含 `GET` 和 `POST`。路由实现、前端客户端、测试、文档、示例和生成的 OpenAPI
  行为都要与此一致。
- 这条 HTTP 限制不禁止 SQL 的 `UPDATE`/`DELETE`、数据库权限、迁移、外键动作或仓储层内部操作。不要把数据库
  术语当成 HTTP 方法去改写。

## 更改日志

- 每个值得注意的改动都记录在 `changelog/CHANGELOG.md` 中与改动领域对应的小节下。所谓值得注意，是指队友读 diff
  而不是读日志才发现它时会感到意外。
- 每条记录写成一对行，先英文后简体中文，与文件其余部分一致。写清楚改动为什么重要，而不只是动了什么：diff 已经
  记录了动了什么。
- `changelog/CHANGELOG.md` 是唯一在用的团队改动记录。`changelog/work-packages/` 下现有文件是只读的历史档案；不要
  新建或续写个人或分轨日志。
- 完整约定见 `changelog/README.md`。

## 项目状态同步

- GitHub Issues 是可执行的 backlog。`TODO.md` 和 `TODO.zh-CN.md` 是带优先级的摘要，必须链接到 Issue，而不是维护
  一份独立的工作清单。
- `README.md` 和 `README.zh-CN.md` 要与当前用户可见的功能、Schema/运行时要求和 staging 入口保持一致。不要让已上线的
  功能仍被描述为缺失。
- 当一个贡献改变了已上线行为或可执行 backlog 时，在同一个 pull request 中同步共享 changelog、相关 README 和两份
  TODO 摘要；如果改动涉及答辩材料，还要同步 `docs/presentation/TALKING_POINTS.md`（值得展示的内容）和
  `docs/presentation/REFLECTION.md`（仍然薄弱的地方）。计划中的事项上线后，在那里标为完成并附上 PR 号。
- 每份 Markdown 文档都同时有英文（`X.md`）和简体中文（`X.zh-CN.md`）版本，在同一个 pull request 中一起修改。带日期的
  记录（压测和扫描报告、changelog 中过去的条目）保持原样，只在会误导读者时加注说明。
- 每个 pull request 都要检查 changelog、README、TODO、关联 Issue、测试、迁移、密钥和部署影响。更新受影响的记录，
  或说明每一项为什么是 `N/A`。
- 运行时改动合并后并不算完成。要核实自动部署到达了确切的合并 SHA，检查健康状态和受影响的用户流程，然后在关闭
  Issue 前附上这些证据链接。
- 使用 `.github/pull_request_template.md` 中的证据清单。绝不把被跳过的集成测试说成通过，需要部署证据时绝不在合并时
  就关闭 Issue。
