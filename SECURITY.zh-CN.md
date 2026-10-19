# 安全策略

[English](SECURITY.md) | 简体中文

SecureView 是 Monash FIT3162 的毕业设计项目，由学生团队维护，不是公司，也没有漏洞赏金。
但我们仍然希望收到安全问题的报告，并会修复它们。

## 报告漏洞

请私下报告。不要为安全问题开公开的 issue、pull request 或 discussion。

- 发邮件到 `swen0027@student.monash.edu`，主题以 `[SecureView] Security` 开头。这是团队的
  联系地址，和网站 **Contact us** 页面用的是同一个。
- 如果你有本仓库的访问权限，也可以在 **Security → Advisories → New draft security advisory**
  新建一个草稿安全公告。只有维护者能看到。

请写明你发现了什么、复现步骤、受影响的提交或页面，以及攻击者能借此做什么。请使用你自己的测试账号，
不要发送别人的数据。

我们会尽快回复，告诉你能否复现、打算怎么处理，并在修复后通知你。如果你愿意，可以在更新日志里署名。

## 范围

在范围内：

- 本仓库中的代码：Vue 前端（包括浏览器内的加密）、FastAPI 后端、MySQL 表结构及其权限，以及
  `deployment/` 下的部署脚本。
- 部署在 `https://secureview.tech` 的 staging 环境，但须遵守下面的规则。

不在范围内：

- 第三方服务或库中已公开的问题。请向上游报告；如果 SecureView 受到的影响超出上游建议覆盖的范围，
  再告诉我们。
- 需要已被攻破的设备、恶意浏览器扩展或物理接触才能利用的问题。
- 没有实际影响的“缺少最佳实践响应头或配置”。
- 针对团队成员或教学人员的社会工程。
- 威胁模型中已记录为“接受”的风险。请先查看 [docs/THREAT_MODEL.zh-CN.md](docs/THREAT_MODEL.zh-CN.md)。

## 不要做的事

- 不要用别人的账号在线上环境测试，也不要尝试读取、修改或删除别人的文件。请注册你自己的账号。
- 不要做破坏性测试：不做压力测试或拒绝服务测试，不批量注册账号，不尝试写满磁盘，不做任何会删除或
  损坏数据的事。
- 未经事先询问，不要对 `https://secureview.tech` 运行自动化扫描器。服务器是共用的，并有按地址的
  限流。
- 不要尝试访问服务器本身（SSH、MySQL、CI runner）。它们不在范围内。
- 一旦证明了问题就停下来报告。不要保留或分享你看到的任何数据。

如需做破坏性测试，请在本地运行整套系统。[README.zh-CN.md](README.zh-CN.md) 说明了做法，
[security-lab/](security-lab/) 里有团队自己的攻击脚本。

## 延伸阅读

- [docs/THREAT_MODEL.zh-CN.md](docs/THREAT_MODEL.zh-CN.md)：保护什么、防范谁，以及问题登记表。
- [docs/SECURITY_FLOWS.zh-CN.md](docs/SECURITY_FLOWS.zh-CN.md)：加密、分享和恢复流程如何工作。
- [docs/security/](docs/security/)：按日期存放的扫描报告。
