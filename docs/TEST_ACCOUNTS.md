# Test accounts

[简体中文](TEST_ACCOUNTS.zh-CN.md)

> The repository is private. These accounts exist **only in the disposable local test database**
> (`fyp_secure_file_platform_test`), used for UI audits and video recording. Never use them on staging or any real
> environment, and never register accounts with these names on staging.

## 1. Local test accounts (UI audit, video recording)

The login password and the encryption passphrase are different things: the password only signs you in, the passphrase
unlocks the private key. They must differ.

| Role | Username | Login password | Encryption passphrase |
| --- | --- | --- | --- |
| Alice (file owner) | `demo-alice` | `Dd4&M5Gcu4Na8hKg5xg1` | `demo alice passphrase b0kihlsw4zUc` |
| Bob (recipient) | `demo-bob` | `Aa1!EEchw-Nzsv6sKVmlikg` | `demo-bob passphrase O2P0h29GDJjSSQ` |
| Sam | `sam` | `Kq7!9ddf32ec2bce1e51` | `river lantern d44bdb977da2` |
| Alex | `alex` | `Aa1!eLi2yJSGw5joBTVxm3c` | `alex passphrase j8CqbkY-pgWu-A` |
| Local admin | `demo-uploader-a259c1` | `Aa1!oldX3Oq1EvEuotl56xBAcd26` | `demo passphrase yAyzNmGYj59DgLUqra3mU5QN` |

If the local database is rebuilt these accounts disappear. Register them again against the local `live_server.py`
(no real email needed locally; verification codes land in `E2E_MAILBOX_DIR`) and update this file. Account file format
(the audit script reads it through the `ACCOUNTS` environment variable):

```json
{"alice": {"username": "demo-alice", "password": "…", "passphrase": "…"},
 "admin": {"username": "demo-uploader-a259c1", "password": "…", "passphrase": "…"}}
```

## 2. Demo accounts on staging (https://secureview.tech)

For the live demo and the tamper demo only (see [DEMO_SCRIPT.md](presentation/DEMO_SCRIPT.md),
[TAMPER_DEMO.md](presentation/TAMPER_DEMO.md)).

| Username | Login password | Encryption passphrase |
| --- | --- | --- |
| `demo-alice` | `mcs21666` | demo-alice-passphrase-2026 |
| `demo-bob` | `mcs21666` | demo-bob-other-passphrase-2026 |

- Usernames must start with `demo-`; the tamper tool (`backend/scripts/demo_tamper.py`) refuses other accounts.
- Do not sign in or register on staging through a browser for UI checks. Audits and recordings run locally.
