# 帮助页视频

[English](README.md) | 简体中文

由 `frontend/scripts/record-walkthroughs.mjs` 从真实产品录制，不是模拟画面：

| 文件 | 内容 |
| --- | --- |
| `how-it-works.mp4` | 动画讲解（`/how-it-works?present`），七个场景，每个八秒 |
| `encrypt-upload.mp4` | 登录、选择文件、选择加密算法、点 Start Encryption、带计时的加密步骤与字节对比、密文预览 |
| `share-open.mp4` | 核对对方密钥指纹后分享给另一个账户，该账户用自己的 passphrase 解密，再把文件放进自己的文件夹 |

每个视频都有一张 `.jpg` 封面。账户是虚构的（`sam`、`alex`、`@example.com`），运行在一次性的本地环境里；
密码和 passphrase 由页面遮挡，且都是用完即弃的值。三个视频均在 2026-10-05 “Sealed”改版（侧边栏、
居中页头、两栏设置页、新登录页）之后重新录制。那是在 PR #215 之前，所以 `encrypt-upload.mp4` 里仍是旧的算法下拉框
（没有等级和说明框），完成后也仍是旧的“Encryption Complete”按钮，现在页面上显示的是绿色状态。字幕为英文，视频没有声音。字幕、描边和登录辅助函数与
演示备用视频共用，位于 `frontend/scripts/lib/video.mjs`。

界面改动后重新录制：启动本地环境（API、MySQL、`npx vite`），用 `backend/scripts/seed_test_account.py`
创建两个账户，把它们的凭据写进 JSON 文件
`{ "sam": {username, password, passphrase}, "alex": {...} }`，然后在 `frontend/` 下运行：

```bash
node scripts/record-walkthroughs.mjs --base http://localhost:5173 --accounts accounts.json --out public/videos
```

`--only encrypt-upload,share-open` 只重录这两个。`share-open` 依赖 `encrypt-upload` 上传的文件。
需要 PATH 中有 ffmpeg。提交前逐帧检查结果。
