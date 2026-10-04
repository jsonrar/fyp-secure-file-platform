# 4 分钟现场演示脚本

[English](DEMO_SCRIPT.md)

演示时段是 12 分钟展示里的 3:30–7:30（[TALKING_POINTS.zh-CN.md](TALKING_POINTS.zh-CN.md) 第 0 节）。
目标是让观众记住三件事：文件离开浏览器之前就已经加密；只有指定的人能打开；文件被改动就会被拒绝。
全部在 staging（`https://secureview.tech`）上进行。

## 角色与准备

| 角色 | 位置 | 登录账号 |
| --- | --- | --- |
| 演讲者（“Alice”） | 浏览器窗口 A，屏幕左半边 | `demo-alice` |
| 同事（“Bob”） | 浏览器窗口 B，屏幕右半边，**使用另一个浏览器用户配置**，两个会话互不干扰 | `demo-bob` |
| 攻击者 | 一个终端，到第 4 步之前先最小化 | VPS 的 root |

`demo-alice` 和 `demo-bob` 已经在 staging 上建好（2026-10-04 用种子脚本创建，不需要邮箱验证码；登录密码 `mcs21666`，
passphrase 由项目负责人保管）。用户名必须以 `demo-` 开头，因为篡改工具会拒绝其他账号。两个账号的口令要互不相同，也不要和任何真实
账号相同。

展示前，用 `demo-alice` 上传 `quarterly-results.txt`（一个简短、能直接看懂的文本文件），并分享给
`demo-bob`。第 4 步篡改的就是这个预先分享好的文件，这样可以提前查好它的 id；第 1 步现场上传的文件
是新的，它的 id 事先不知道。

## 脚本

| 时间 | 步骤 | 操作 | 讲解 |
| --- | --- | --- | --- |
| 0:00–0:15 | 交代场景 | 指一下两个窗口 | “Alice 要把一份机密报告发给 Bob。他们俩都不信任服务器，你们也不应该信任。” |
| 0:15–1:15 | **1. 上传** | 窗口 A：Upload → 选择 `board-minutes.pdf` → Start Encryption，让步骤动画播完 | “你看到的每一步耗时都是真实测出来的：在浏览器里用一把新密钥加密，再把这把密钥包装起来，然后上传。看这些字节：原文件开头是 `%PDF`，服务器收到的是一堆乱码。” |
| 1:15–2:05 | **2. 分享** | 窗口 A：My Files → `board-minutes.pdf` → Share → 输入 `demo-bob` → Share。确认页显示 Bob 的密钥指纹。窗口 B：Settings 里显示同一个指纹 | “发送之前，Alice 能看到文件会被锁到哪一把密钥上。Bob 从自己的设置页读出指纹：两边一致，所以只有 Bob 能打开。服务器从头到尾没拿到过这把密钥。”然后点 Confirm and share |
| 2:05–2:45 | **3. 打开** | 窗口 B：My Files → Shared with me → `board-minutes.pdf` → Download，打开保存下来的文件 | “Bob 用的是他自己的口令，不是 Alice 的。文件取出时先校验，再在他自己的设备上解密。” |
| 2:45–3:40 | **4. 篡改** | 切到终端，对 `quarterly-results.txt` 执行 [TAMPER_DEMO.zh-CN.md](TAMPER_DEMO.zh-CN.md) 里的 `flip`。窗口 B：下载这个文件 | “现在假设我是服务器管理员，或者入侵了服务器的人。我把一个存储的文件改掉一个字节。”下载被拒绝，这一行变成 **Modified**。“改过了，所以被拒绝。不需要任何人相信我们。” |
| 3:40–4:00 | 收尾 | 切回幻灯片 | “离开设备前就加密，只有指定的人能打开，被改动就拒绝。” |

讲完之后马上执行 `restore`（见 TAMPER_DEMO），再用 `demo-alice` 点一下该文件的状态标签，让它变回
Verified。

## 前一天

- [ ] 两个演示账号都能登录 staging，`quarterly-results.txt` 已从 Alice 分享给 Bob。
- [ ] `demo_tamper.py list --owner demo-alice` 能列出这个文件，并且没有任何文件标着 TAMPERED；
      `flip` 和 `restore` 两条命令已经填好文件 id，可以直接粘贴。
- [ ] 完整计时预演一次，最后执行 `restore`。
- [ ] 备用视频已经录好（见下文），并拷到演示用的电脑上。
- [ ] 展示前两小时内不要往 `main` 合并任何东西。合并会触发自动部署，服务会重启几秒钟。

## 开始前 30 分钟

- [ ] 健康检查：`https://secureview.tech/health/live` 返回 200。
- [ ] 两个窗口都已登录并且**已经解锁**（各自先打开一个文件），免得观众等口令的密钥派生。
- [ ] 浏览器缩放 125%；关掉通知和聊天软件；关掉密码管理器的弹窗。
- [ ] `board-minutes.pdf` 放在桌面上；如果 Alice 的 My Files 里有之前上传的同名文件，先删掉。
- [ ] 准备好手机热点，以防会场网络出问题。

## 出问题时

| 问题 | 处理 |
| --- | --- |
| 断网，或者 staging 没有响应 | 切到备用视频的同一步；视频和本脚本步骤一致 |
| 解锁或下载卡住超过约 10 秒 | 说一句“这里本来会……”，切到视频的这一步 |
| 篡改后下载居然成功了 | 执行 `list`：如果文件没有标 TAMPERED，说明 `flip` 没执行成功；播放视频的第 4 步 |
| 点错了 | 不要现场补救，直接进入下一步 |

## 备用视频

已录好：[`media/demo-backup.mp4`](media/demo-backup.mp4)（2 分 23 秒，无声音，1280×720）。它按本脚本逐步
进行，并标明当前是谁的屏幕（Alice 或 Bob 的浏览器）；第 4 步真的改动了存储的文件：视频里的卡片显示的就是实际执行的
`demo_tamper.py flip` 命令和它的输出，录完后文件已还原。把它拷到演示电脑上，确认断网也能播放。演讲者边放边讲时可以随时
暂停；它故意比 4 分钟的时段短。

它是在一个本地的一次性环境上录的，运行的代码和 staging 完全相同（录制脚本会自动登录，这只在本地环境上做），所以画面一样。
界面改动后要重录，在 `frontend/` 下、本地环境跑着并有两个本地 `demo-*` 账号时执行：

```bash
node scripts/record-demo.mjs --base http://localhost:5173 --accounts accounts.json --tamper tamper.sh --out ../docs/presentation/media
```

`tamper.sh` 负责加载本地环境变量后执行 `backend/scripts/demo_tamper.py "$@"`。
