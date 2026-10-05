# 测试账号

[English](TEST_ACCOUNTS.md)

> 仓库是私有的。这些账号**只存在于本地一次性测试库**（`fyp_secure_file_platform_test`），用来跑界面巡检和录视频。
> 不要把它们用在 staging 或任何真实环境，也不要在 staging 上注册同名账号。

## 一、本地测试账号（界面巡检、录视频）

登录密码和加密口令（passphrase）是两样东西：密码只负责登录，口令用来解锁私钥，两者必须不同。

| 角色 | 用户名 | 登录密码 | 加密口令 |
| --- | --- | --- | --- |
| Alice（文件所有者） | `demo-alice` | `Dd4&M5Gcu4Na8hKg5xg1` | `demo alice passphrase b0kihlsw4zUc` |
| Bob（接收者） | `demo-bob` | `Aa1!EEchw-Nzsv6sKVmlikg` | `demo-bob passphrase O2P0h29GDJjSSQ` |
| Sam | `sam` | `Kq7!9ddf32ec2bce1e51` | `river lantern d44bdb977da2` |
| Alex | `alex` | `Aa1!eLi2yJSGw5joBTVxm3c` | `alex passphrase j8CqbkY-pgWu-A` |
| 本地管理员 | `demo-uploader-a259c1` | `Aa1!oldX3Oq1EvEuotl56xBAcd26` | `demo passphrase yAyzNmGYj59DgLUqra3mU5QN` |

本地库如果被重建，这些账号会消失。到时用本地的 `live_server.py` 重新注册（本地不需要真实邮箱，验证码在 `E2E_MAILBOX_DIR`），
并把新的账号信息更新到这里。账号文件的格式（巡检脚本通过 `ACCOUNTS` 环境变量读取）：

```json
{"alice": {"username": "demo-alice", "password": "…", "passphrase": "…"},
 "admin": {"username": "demo-uploader-a259c1", "password": "…", "passphrase": "…"}}
```

## 二、staging（https://secureview.tech）上的演示账号

只用于现场演示和篡改演示（见 [DEMO_SCRIPT.zh-CN.md](presentation/DEMO_SCRIPT.zh-CN.md)、[TAMPER_DEMO.zh-CN.md](presentation/TAMPER_DEMO.zh-CN.md)）。

| 用户名 | 登录密码 | 加密口令 |
| --- | --- | --- |
| `demo-alice` | `mcs21666` | demo-alice-passphrase-2026 |
| `demo-bob` | `mcs21666` | demo-bob-other-passphrase-2026 |

- 用户名必须以 `demo-` 开头，篡改工具（`backend/scripts/demo_tamper.py`）会拒绝其他账号。
- 不要用浏览器在 staging 上自行登录或注册来做界面检查，巡检和录制都在本地跑。
