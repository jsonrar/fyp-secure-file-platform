# 文件加密信封 — v1

[English](FILE_ENVELOPE.md) | 简体中文

本文是文件上传前如何加密的规范性字节级定义。参考实现为
`frontend/src/crypto/file_envelope.ts`，锁定它的测试向量位于同目录的 `test_vectors.json`。

**在编写第二个实现之前请先读本文。** 服务器从不持有数据加密密钥（DEK），因此它从不计算这个
AAD，也从不认证这个 tag。没有任何服务端检查能发现某个实现把这些字节拼错了 —— 后果只是产出
谁也解不开的文件，而且失败发生在下载时，不是上传时。本项目的账户密钥信封已经因为犯过一次
这个错误，同时存在三套互不兼容的 AAD 构造。

## 1. 套件常量

| 字段 | 取值 |
|---|---|
| `envelope_version` | 1 |
| `aad_version` | 1 |
| `encryption_algorithm` | `AES-256-GCM` |
| `key_wrapping_algorithm` | `RSA-OAEP-SHA256`，SHA-256 MGF1，**空 label** |
| DEK | 32 随机字节，每个文件全新生成 |
| Nonce | 12 随机字节，每次加密全新生成，来自 CSPRNG |
| Tag | 16 字节，与密文**分离**存储 |

Nonce 必须随机，绝不能用计数器。计数器无法在多个标签页或多台设备之间协调，而 GCM 下重复的
(key, nonce) 组合会泄露两段明文的异或值，并可通过恢复认证密钥实现伪造。

## 2. 编码原语

全程无符号大端序。变长字段加长度前缀，定长字段不加。加 frame 正是编码具备单射性的原因 ——
否则可以让相邻字段互相移位，产生相同的字节串。

| 原语 | 定义 |
|---|---|
| `u8(n)` / `u32(n)` / `u64(n)` | 1 / 4 / 8 字节，无符号大端 |
| `uuid16(u)` | RFC 4122 UUID 的 16 个原始字节，不是文本形式 |
| `ascii(s)` | ASCII 字节；非 ASCII 输入报错 |
| `utf8_nfc(s)` | Unicode NFC 归一化后的 UTF-8 字节 |
| `frame(b)` | `u32(len(b)) || b` |
| `||` | 连接 |

这些与后端 `key_service._frame` 一致，因此同一份编码器可同时服务本信封与账户密钥授权摘要。

## 3. AAD-3 —— 文件内容

```
AAD-3 = ascii("FYP-FILE-CONTENT") || 0x00 || u8(aad_version)
      || uuid16(file_id)
      || u32(envelope_version)
      || frame(ascii(encryption_algorithm))
      || u64(plaintext_size)
      || frame(utf8_nfc(original_filename))
      || frame(ascii(lowercase(mime_type)))
```

label 之后的 `0x00` 用于防止某个域分隔标签成为另一个的前缀。

### 不得包含任何按接收方变化的字段

所有者与每个共享接收方使用**同一把 DEK 解密同一份密文**，因此他们必须重建出完全相同的 AAD
字节。故 `key_id`、`wrapped_file_key`、`owner_key_id`、`recovery_key_id` 及授权状态全部排除
—— `FileCryptoEnvelopeOut` 返回的是**调用者自己的** key id，绑定它会导致每个共享文件对接收方
都无法解密。

### 文件名、MIME 类型与大小是刻意绑定的

服务器以明文列存储这三项，本可随意改写：把某份文档以另一个名字提供给接收方，或通过错误标注
类型来影响客户端的处理方式。绑定它们之后，任何此类修改都会变成解密失败。

代价是**这三个字段在密文的整个生命周期内不可变**。当前这是成立的 —— `file_router` 只暴露
上传、列表、获取、下载、删除与完整性检查，不存在改名或元数据更新路由 —— 但将来的改名功能无法
就地修改这些列，只能以新信封重新加密，或升级到 `envelope_version = 2` 把文件名移入
`encrypted_manifest`。**在设计任何改名功能之前，必须先记录这条约束。**

### 归一化是规范的一部分

必须施加与 `FileUploadMetadata` 相同的规则，并发送归一化后的取值，以保证上传时参与哈希的
字符串与下载时返回的字符串逐字节一致：

- `original_filename`：Unicode **NFC**，1–255 字符，无首尾空白，不含 `/ \` 路径分隔符，
  不含 Unicode `Cc` 类字符，不为 `.` 或 `..`，且不以空格或句点结尾。
- `mime_type`：**转为小写**，匹配 `^type/subtype$` 且不带参数，3–150 字符。

## 4. 分离 tag

`crypto.subtle` 返回 `ciphertext || tag` 拼接成的单一缓冲区。API 单独存储 tag，且存储的密文
不含 tag，因此实现必须在加密后拆分、解密前重新拼接：

```
encrypt:  out        = AES-GCM(dek, nonce, plaintext, AAD-3)
          ciphertext = out[0 .. len-16]
          auth_tag   = out[len-16 .. len]

decrypt:  plaintext  = AES-GCM-open(dek, nonce, ciphertext || auth_tag, AAD-3)
```

这一点在数值上被强制：`file_service` 会拒绝密文长度与 `plaintext_size` 不一致的上传。拼接后的
缓冲区正好多出 16 字节，会在那里被拒。

## 5. 上传载荷

`POST /files` 接收 multipart：密文主体加一个 JSON metadata 部分。

| metadata 字段 | 来源 |
|---|---|
| `file_id` | 客户端生成的 RFC 4122 v4 UUID |
| `original_filename`、`mime_type`、`plaintext_size` | 按 §3 归一化 |
| `encryption_algorithm`、`envelope_version`、`aad_version` | 见 §1 |
| `nonce`、`auth_tag` | 规范 Base64，12 与 16 字节 |
| `owner_key_id`、`wrapped_file_key` | DEK 包装给所有者的活跃公钥 |
| `recovery_key_id`、`recovery_wrapped_file_key` | DEK 包装给活跃的恢复公钥 |
| `key_wrapping_algorithm` | `RSA-OAEP-SHA256` |

所有二进制字段一律使用带 `+/` 与强制 `=` 填充的标准 Base64 —— 绝不使用 URL-safe，绝不省略
填充。API 会拒绝任何重新编码后与原字符串不一致的取值。

## 6. 强制自检

服务器无法验证这份密文能否解出任何东西。写出一个结构合法却打不开的信封，明文一旦丢弃，该
文件就永久丢失。因此以下检查是强制要求，而非防御性措施。

**上传前**：用该 DEK、nonce、tag 与 AAD-3 解密刚生成的密文，确认明文与输入逐字节一致；确认
密文长度等于 `plaintext_size`。在 `MAX_UPLOAD_SIZE_BYTES` 的 25 MiB 上限下，这个开销可以承受。

**共享前**：从自己的包装中解出 DEK，并**确认它能打开该文件**，然后才可 rewrap 给任何人。
接收方的私钥不可得，因此 rewrap 本身无法验证；共享一把打不开文件的 DEK 会产生一个对接收方
静默失效的授权。同时应从 PEM 重算接收方公钥指纹并展示 —— 除此之外没有任何机制把那把密钥
绑定到目标本人。

**完全无法验证**：恢复包装。恢复私钥保存在离线环境，客户端无从确认
`recovery_wrapped_file_key` 能解出该 DEK。错误或被替换的恢复密钥只有在真正尝试恢复时才会被
发现，可能已是数年之后。缓解方式：固定并显示恢复公钥指纹，在其未经带外公告而变化时拒绝上传，
并定期对真实上传演练恢复流程。

## 7. 版本迁移

`envelope_version` 与 `aad_version` 相互独立：新的 AAD 布局未必意味着信封形状发生变化。必须
拒绝任何自身未实现的版本，并报告为「版本不受支持」，不得猜测也不得回退 —— 能够通过声明某个
较弱套件把客户端拉过去的服务器，就掌握了一次降级攻击。文件信封实际上不可变，因此只要还存在
任何 v1 文件，就必须保留 v1 的解密能力。
