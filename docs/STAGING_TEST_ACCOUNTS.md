# Staging Test Accounts

[English](STAGING_TEST_ACCOUNTS.md) | [简体中文](STAGING_TEST_ACCOUNTS.zh-CN.md)

This runbook provisions reusable **application accounts** for the staging deployment. It does
not create MySQL identities and must never be used for production accounts.

## Provisioned staging identities

The MCS21 staging database was provisioned and verified on 2026-08-12 with these identities:

| Username | Application role | Intended test use |
|---|---|---|
| `admin` | `ADMIN` | Authentication and future administrator authorization tests |
| `test_user_1` | `USER` | File owner/uploader test actor |
| `test_user_2` | `USER` | Sharing recipient and access-revocation test actor |

All three accounts were confirmed `ACTIVE`. Each completed a real login and authenticated
`/api/v1/auth/me` request through the host Nginx entry point. The provisioner also logs out
its verification session so routine rechecks do not leave an active session behind.

The current implementation boundary still applies: registration, login, session, and
`/auth/me` flows are operational, while file, sharing, audit-query, recovery, and admin
business endpoints deliberately return `501 feature_not_implemented`.

## Secret handling

No password or RSA private key is committed to Git. On the staging VPS, the provisioner writes
them under `/srv/mcs21/test-accounts/`:

- the directory is mode `0700`;
- `credentials.json` and every `*-private-key.pem` file are mode `0600`; and
- the script never prints a password, access token, or private key.

Obtain credentials from the authorized project owner or the restricted VPS directory. Do not
paste them into GitHub, chat, issue trackers, screenshots, or deployment logs. The repository
ignores `test-accounts/` directories and PEM files as a second line of defence, but filesystem
permissions and careful handling remain mandatory.

## Running the provisioner

Prerequisites on the deployment host:

- the application is reachable through host Nginx at `http://127.0.0.1`;
- the backend container is running as `mcs21-staging-backend-1` (or pass `--container`);
- the operator can run `docker exec`; and
- `/srv/mcs21/test-accounts/` is outside every Git worktree.

From the repository root on the VPS:

```bash
sudo python3 scripts/provision_staging_test_accounts.py
```

Use explicit overrides only when the deployment differs:

```bash
sudo python3 scripts/provision_staging_test_accounts.py \
  --base-url http://127.0.0.1 \
  --container mcs21-staging-backend-1 \
  --output-dir /srv/mcs21/test-accounts
```

The first run registers each account through the normal API so password hashing, RSA key
generation, account persistence, and registration audit behaviour are exercised. It then sets
the fixed staging roles inside the backend container because the administrator API is not yet
implemented. This out-of-band role assignment is staging-only operational setup and is not a
replacement for an audited administrator workflow.

Later runs reuse the saved credentials, reapply the declared roles, and repeat login/role/logout
verification. If an account already exists but its saved credential is unavailable, registration
fails and the script stops; it does not guess or reset the password. Missing saved private keys,
an unhealthy application, a role mismatch, or a failed authentication step also stops the run.

Coordinate account disablement, deletion, or password rotation as a separate staging change.
Do not delete the private keys while encrypted test data still depends on them.
