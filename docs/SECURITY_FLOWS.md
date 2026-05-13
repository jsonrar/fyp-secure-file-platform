# Security Flows

## Upload Flow

```text
User uploads file
    ↓
Backend validates login session
    ↓
Generate random AES-256 file key
    ↓
Encrypt file using AES-256-GCM
    ↓
Calculate SHA-256 hash of encrypted file
    ↓
Store encrypted file in encrypted_files/
    ↓
Delete temporary plaintext file
    ↓
Wrap AES file key using owner's public key
    ↓
Wrap AES file key using recovery public key
    ↓
Save metadata and wrapped keys in database
    ↓
Write audit log
```

## Download Flow

```text
User requests download
    ↓
Backend checks authentication
    ↓
Backend checks file-level permission
    ↓
User provides private key file or private key text
    ↓
Backend unwraps AES file key temporarily
    ↓
Backend verifies encrypted file hash
    ↓
Backend decrypts file temporarily
    ↓
Optional watermark is added
    ↓
Return plaintext file to user
    ↓
Delete temporary decrypted file
    ↓
Write audit log
```

## Share Flow

```text
Owner selects file and target user
    ↓
System checks SHARE permission
    ↓
Owner provides private key
    ↓
Backend unwraps owner's AES file key
    ↓
Backend loads target user's public key
    ↓
Backend wraps AES file key for target user
    ↓
Create file_access_grant
    ↓
Create file_key_wrapping
    ↓
Write audit log
```

## Revoke Flow

```text
Owner selects target user
    ↓
System checks REVOKE permission
    ↓
Mark access_grant as revoked
    ↓
Mark file_key_wrapping as revoked
    ↓
Target user can no longer download through the platform
    ↓
Write audit log
```

## Audit Log Hash Chain

```text
current_hash = SHA256(previous_hash + log_content)
```

If an old log entry is modified, the hash chain will fail verification from that point onward.
