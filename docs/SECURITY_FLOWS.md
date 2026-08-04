# Security Flows

These flows define transaction and trust boundaries. Auth is implemented. Upload, download,
sharing, access revocation, audit-query, recovery, and admin route handlers remain guarded
with `501 feature_not_implemented`; their sections below are requirements, not claims of
working features.

## Shared Preconditions

Every implemented protected request accepts an opaque access token only through
`Authorization: Bearer <token>`. The API dependency resolves its SHA-256 hash to an active,
unexpired server-side session and ACTIVE user, then supplies a trusted `ActorContext`.
Unknown, disabled, expired, revoked, and malformed access credentials receive the same
public authentication response.

Request bodies, authorization headers, passwords, access/refresh tokens, private keys,
wrapped keys, and plaintext filenames must be excluded from application, proxy, and tracing
logs. All Auth responses are non-cacheable. Client IP comes from the direct request peer;
deployments must configure a trusted proxy boundary before using forwarded-address headers.

## Password Policy

Passwords are Unicode NFC-normalized before policy evaluation, hashing, and comparison.
New passwords must contain 15 to 128 characters and must not equal a normalized username,
email address, email local part, or entry in the local common-password blocklist. Accepted
passwords are hashed with `pwdlib`'s recommended Argon2id configuration. Login upgrades a
valid stored hash when the recommended parameters change.

The local blocklist intentionally contains only a small set of high-risk defaults. It is
useful for this FYP but is not a maintained breached-password corpus. Production should
replace or extend it with a regularly updated source without weakening the 15-character,
NFC, or Argon2id rules.

## Registration

```text
Normalize and validate username/email/password
  -> consume the database-backed registration IP throttle bucket
       bucket key = HMAC-SHA-256(application secret, scope || client IP)
  -> check case-insensitive username/email uniqueness
  -> hash password with Argon2id
  -> generate configured RSA key pair (3072 bits by default)
  -> fingerprint the canonical DER public key with SHA-256
  -> begin one transaction
       insert USER account with public UUID
       insert public key and fingerprint; never insert private key
       append AUTH_REGISTERED audit event while locking the chain head
       commit
  -> return the private key exactly once over TLS with no-store/no-cache headers
```

The client should force a private-key file download and avoid browser storage. If the
committed response is lost, the server cannot reproduce the private key; a future explicit
key rotation/recovery workflow is required. Registration never accepts role, status, or
verification state from the client.

## Login and Access Authentication

```text
Normalize username
  -> derive database throttle buckets for account and direct client IP
       key = HMAC-SHA-256(application secret, scope || normalized value)
  -> inspect both persisted failure buckets under sorted row locks
  -> reject an active block with 429 and Retry-After
  -> acquire a non-blocking worker memory slot or fail fast with 429
  -> perform real-or-dummy Argon2id verification
  -> clear the account bucket on success, or atomically record completed failures
  -> append a generic failure audit event without a plaintext throttle identifier
  -> lock ACTIVE user and transparently upgrade a valid legacy bcrypt hash to Argon2id
  -> enforce maximum active-session count, evicting oldest families
  -> generate independent high-entropy access and refresh credentials
  -> store only access SHA-256 on user_sessions
  -> store refresh SHA-256 generation 0 in session_refresh_tokens
  -> update last login and append AUTH_LOGIN_SUCCEEDED in the same transaction
  -> return both raw credentials once
```

The account and IP buckets use separate limits (the IP threshold is deliberately higher for
shared networks). MySQL makes completed failure counts consistent across workers, while each
worker independently bounds in-flight Argon2 memory. These controls do not replace edge
rate limiting, trusted-proxy configuration, cleanup of stale buckets, or distributed
denial-of-service protection.

Each authenticated request hashes its raw access token and loads the corresponding user and
session. Status, access expiry, absolute expiry, and user status are checked before creating
the `ActorContext`. The raw token never enters the context or a database row.

## Refresh Rotation and Replay

```text
Validate refresh credential shape
  -> hash token and resolve its internal user/session route without trusting it
  -> lock user, parent session, then refresh-token record in a fixed order
  -> if already consumed:
       revoke access plus every refresh credential in that session family
       append AUTH_REFRESH_REPLAY_DETECTED
       commit revocation and return generic invalid_refresh_token
  -> reject revoked, expired, inactive, disabled, or absolute-expired family
  -> enforce a per-session minimum interval before another rotation can be consumed
  -> mark current refresh generation consumed
  -> generate a new independent access/refresh pair
  -> replace access hash and insert the next refresh generation
  -> append AUTH_SESSION_REFRESHED and commit
```

A refresh token is therefore single-use. Rotation invalidates the prior access token as
well as consuming the prior refresh token. Refresh lifetime cannot exceed the absolute
session lifetime, so repeated rotation cannot create an immortal session. The locked
per-session minimum interval bounds refresh-row and global-audit-chain growth; deployment
edge limits and expiry-based cleanup/archival are still required for overall capacity.

## Logout, Session Revocation, and Password Change

- Logout locks and revokes the current session family, including unconsumed refresh tokens.
- Logout-all revokes every ACTIVE session family owned by the authenticated account.
- Session listing returns bounded public metadata and UUIDs, never token hashes or internal
  IDs. Individual revocation is scoped by both actor user ID and public session UUID.
- Password change reads and verifies the current hash before acquiring the user write lock,
  then rechecks the hash under lock before updating it. It applies the full policy, writes a
  new Argon2id hash, and revokes every active session family, including the caller's current
  session. Failed current-password checks use dedicated reauthentication account/IP buckets,
  so they cannot lock the public login buckets; only completed checks increment them. The
  client must log in again.

Each state change and its audit event share one application-service transaction.

## Auth Features Requiring External Channels

Forgotten-password reset, email verification, MFA, and external identity federation are not
implemented. Secure implementations require, respectively, a trusted recovery-delivery
channel, verified email delivery, enrolled second-factor custody, or a configured identity
provider. Adding unauthenticated endpoints without those trust anchors would create account
takeover paths. `email_verified` is reserved metadata and is not currently enforced at
login.

## Upload (Not Implemented)

```text
Authenticate actor and enforce upload size/type policy
  -> allocate random staging object under the configured storage root
  -> generate one AES-256 file key and 96-bit GCM nonce
  -> stream/bound the upload through versioned AES-GCM encryption
  -> authenticate stable metadata as AAD
  -> hash the complete encrypted envelope
  -> wrap AES key for owner and active recovery public key
  -> begin DB transaction
       insert file metadata, owner grant, and key wrappings
       append audit entry and atomically publish staged object
       commit
  -> compensate storage and roll back on failure
```

The AES key, storage root/path, staging name, and wrapped-key bytes must never enter a
response. Crash-created orphan objects require a scheduled reconciliation job.

## Download (Not Implemented)

```text
Authenticate actor
  -> load active file scoped to actor
  -> require active DOWNLOAD grant and matching active user wrapping
  -> verify encrypted-object hash before decryption
  -> accept private key only on a dedicated no-body-logging endpoint
  -> verify key type/size/fingerprint and unwrap AES key in memory
  -> decrypt/authenticate, optionally watermark, stream, and clean temporary plaintext
  -> append success/failure audit event without secret fields
```

The planned server-side decrypt flow temporarily sees the user's private key and is not
end-to-end encryption. Production custody should move private-key operations to a trusted
client or hardware-backed key service.

## Share and Revoke (Not Implemented)

Sharing must authenticate the actor, require SHARE policy, load an ACTIVE target public key,
rewrap the file key, and create/reactivate the grant, wrapping, and audit event atomically.
Revocation must require REVOKE policy, forbid revoking the canonical owner, and atomically
revoke the target grant and matching wrappings. Revocation cannot remove plaintext already
downloaded by a recipient.

## Recovery (Not Implemented)

Recovery must enforce maker-checker separation, time-bounded conditional state transitions,
isolated private-key use, and an audit event in the same transaction. Production recovery
keys belong in an offline or hardware-backed process; the planned web flow is an explicitly
constrained FYP demonstration.

## Audit Chain

```text
lock singleton audit_chain_heads row FOR UPDATE
canonical_event = deterministic JSON of immutable audit fields
current_hash = SHA-256(previous_hash || canonical_event)
insert audit row and update chain head inside the use-case transaction
```

Migration `0002_auth_identity_sessions` seeds the genesis head only for an empty audit table.
It refuses a non-empty revision-0001 audit history because that release used an incompatible
payload and had already discarded datetime microseconds; adopting such data requires a
reviewed migration and external checkpoint. The head lock prevents concurrent Auth
transactions from forking the new chain. Entries use persisted `DATETIME(6)` values and
canonical `{}` metadata, and restrictive user foreign keys prevent a cascade from mutating
hashed actor/target IDs; users referenced by history must be soft-deleted. A database-resident
plain hash chain cannot stop an administrator from rewriting and recomputing all history, so
stronger deployments must periodically publish a signed/HMAC checkpoint outside the audit
database.
