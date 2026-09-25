# Observability, external audit checkpoints, and incident response

[English](OBSERVABILITY_AND_INCIDENT_RESPONSE.md) | [简体中文](OBSERVABILITY_AND_INCIDENT_RESPONSE.zh-CN.md)

This runbook is the operational contract for issue #59. It deliberately keeps telemetry
**metadata-only**: operators need to know that an authentication, storage, schema, recovery, or
deployment event happened, but logs and alerts must never become a second copy of the data the
application is protecting.

## 1. Data-minimising structured logs

`backend/app/core/observability.py` installs a one-line JSON formatter for the `app.*` logger
hierarchy. Security events use a fixed field allow-list (`event`, `category`, `outcome`, route
template, status, duration, request id, vetted client IP, and similarly bounded operational
fields). Unknown extras are discarded. The final formatter also removes Bearer credentials,
secret assignments, and PEM private-key blocks from legacy/free-text messages.

The HTTP middleware records **route templates**, never the raw URL. A request for
`/api/v1/recovery/real-user-value/approve` is therefore represented as
`/api/v1/recovery/{request_id}/approve`. Request/response bodies are never inspected by the
observability layer.

Events currently emitted include:

| Category | Event | Trigger |
|---|---|---|
| `auth` | `auth_rate_limited` | an authentication route returns 429 |
| `storage` | `storage_unavailable` | storage service raises its bounded availability error |
| `storage` | `integrity_verification_rejected` | altered/missing ciphertext is refused |
| `database` | `database_unavailable` | readiness cannot execute its DB probe |
| `schema` | `schema_mismatch` | deployed DB revision differs from the application contract |
| `recovery` | `recovery_operation` | any recovery route succeeds or is rejected |
| `application` | `unhandled_application_error` | an unexpected exception reaches the global handler |
| deployment | existing `mcs21-deploy` audit record | deploy/rollback result, caller, commit/target and rollback point |

The deployment log already records bounded key/value fields in `/var/log/mcs21-deploy/audit.log`
and journald. It does not contain environment contents, database passwords, application secrets,
request bodies, filenames, or private keys. Keep this separate root-owned log as the deployment
source of truth; do not replace it with command tracing (`set -x` is forbidden on production
scripts).

### Never log or alert

The following are prohibited in application logs, systemd journal messages, monitor state, and
alert payloads:

- `Authorization`/refresh tokens, cookies, session hashes, verification/reset codes;
- passwords, encryption passphrases, API keys, database credentials, HMAC keys;
- PEM/private-key material, wrapped private-key plaintext, recovery private keys;
- plaintext file content, plaintext filenames, MIME supplied by users;
- complete email bodies or recipient addresses;
- arbitrary request/response bodies or exception locals.

`EMAIL_PROVIDER=console` is still development-only, but it now logs only that a message was
suppressed; it no longer prints recipient, subject, verification code, reset content, or body.
Unit tests seed conspicuous secret strings and fail if those strings reach the formatted log or
monitor/checkpoint artifacts.

## 2. Metrics and actionable alerts

The backend exposes Prometheus text at `GET /internal/metrics`. **nginx does not proxy this
path**, and the production backend binds to `127.0.0.1`; the operations monitor calls it directly
on loopback. Do not add a public nginx location for this endpoint.

Metrics contain only counters over fixed categories and FastAPI route templates:

- `secureview_http_requests_total{method,route,status_class}`;
- `secureview_security_events_total{category,event,outcome}`;
- request-duration sum/count.

`backend/scripts/ops_monitor.py` polls `/health/ready` and `/internal/metrics` every five minutes,
keeps only numeric counters in `/var/lib/fyp-secure-file-platform/ops-monitor/state.json`, and
alerts on **deltas** so old failures do not page forever. A backend restart (counter reset) starts
a fresh baseline.

| Condition in one 5-minute polling interval | Threshold | Action/owner |
|---|---:|---|
| readiness not `ready` / metrics unreachable | 1 | immediate failure; project deployment/test owner |
| auth requests rate-limited | 20 | investigate abuse, proxy/IP handling, fail2ban; deployment/test owner |
| storage unavailable | 1 | inspect filesystem/disk/service; deployment/test owner |
| ciphertext integrity rejection | 1 | investigate the file/storage path as a potential corruption/tamper event |
| schema mismatch | 1 | stop deploys; reconcile release/migration state |
| database unavailable | 1 | inspect MySQL/TLS/disk/network before retrying |
| unexpected application exception | 1 | inspect the redacted event and reproduce without dumping request data |
| rejected recovery operations | 5 | review recovery workflow/role abuse; security owner |

`mcs21-ops-monitor.service` exits non-zero on a threshold or health failure.
`OnFailure=mcs21-alert@%n.service` therefore reuses the tested email alert path from #57. The
actual recipients stay in `/etc/fyp-secure-file-platform/alert.env`, not in the repository.

## 3. Trusted proxy and client IP policy

The application does **not** parse `X-Forwarded-For` or `X-Real-IP` itself. `RequestContext`
uses `request.client`, and the observability middleware does the same.

The only production HTTP path is:

```text
Internet client -> nginx :443 -> Uvicorn 127.0.0.1:8000
```

Uvicorn must run with:

```text
--proxy-headers --forwarded-allow-ips=127.0.0.1
```

That means forwarded headers are accepted only when the TCP peer is local nginx. A direct remote
client cannot reach the loopback-bound backend and cannot make Uvicorn trust a forged forwarded
address. `mcs21-deploy` already uses the same restriction for its preflight instance. Before
claiming #59 staging-complete, record the real unit with:

```bash
systemctl cat fyp-backend | grep -F -- '--forwarded-allow-ips=127.0.0.1'
ss -ltnp | grep '127.0.0.1:8000'
```

If either check fails, stop and correct the service before relying on IP-based throttling,
fail2ban correlation, or audit IP metadata.

## 4. HMAC audit checkpoints outside MySQL

The application's audit chain is append-only in MySQL, but a database-only chain head is not an
independent trust anchor. `backend/scripts/audit_checkpoint.py` signs a minimal snapshot:

```json
{
  "format": 1,
  "created_at_utc": "...",
  "last_log_id": 123,
  "current_hash": "<sha256>",
  "schema_revision": "0006_chacha20_poly1305"
}
```

The record carries `hmac_sha256 = HMAC-SHA256(canonical payload)`. No audit description,
metadata, identity, filename, file content, token, or key material is copied into the checkpoint.
The HMAC key comes only from `AUDIT_CHECKPOINT_HMAC_KEY`.

The production timer publishes hourly. The local 0600 copy is written under
`/var/lib/fyp-secure-file-platform/audit-checkpoints`; `AUDIT_CHECKPOINT_DEST` **must** point to an
external destination (`s3://...` or `user@host:/...`). On staging, use a dedicated prefix in the
existing locked/retained S3-compatible offsite store. The destination account should be put-only
where practical, and the HMAC key must not be stored in the database or committed to Git.

Example `/etc/fyp-secure-file-platform/audit-checkpoint.env` (0600 root):

```bash
AUDIT_CHECKPOINT_HMAC_KEY=<random >=32-byte secret>
AUDIT_CHECKPOINT_DEST=s3://<locked-bucket>/secureview-audit-checkpoints
AUDIT_CHECKPOINT_S3_ENDPOINT_URL=<S3-compatible endpoint if needed>
# AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY are deployment secrets, never repository values.
```

Generate the key without printing it into shell history, for example by writing it directly into
a root-only file from a password manager. Do not paste the real key into an issue or terminal
screenshot.

### Independent verification

Copy/download checkpoints to a **different machine** and provide the HMAC key through that
machine's environment, then run:

```bash
cd backend
AUDIT_CHECKPOINT_HMAC_KEY='...' .venv/bin/python scripts/audit_checkpoint.py \
  --verify /path/to/downloaded/checkpoints
```

Verification fails if any HMAC is invalid, the timestamp sequence moves backwards, or
`last_log_id` moves backwards. A valid old checkpoint therefore remains evidence even if the
application database is later rewritten. Retain external objects using the same object-lock or
append-only policy as the offsite backup; otherwise an attacker able to delete every old
checkpoint can erase the anchor history.

## 5. Install on staging

After the PR is merged and the exact merge SHA is deployed:

```bash
R=/opt/mcs21/current
cat "$R/.mcs21-release"

sudo install -d -o fypapp -g fypapp -m 0750 \
  /var/lib/fyp-secure-file-platform/ops-monitor \
  /var/lib/fyp-secure-file-platform/audit-checkpoints

sudo install -o root -g root -m 0644 \
  "$R/deployment/server/mcs21-ops-monitor.service" \
  "$R/deployment/server/mcs21-ops-monitor.timer" \
  "$R/deployment/server/mcs21-audit-checkpoint.service" \
  "$R/deployment/server/mcs21-audit-checkpoint.timer" \
  /etc/systemd/system/

sudo systemctl daemon-reload
sudo systemd-analyze verify \
  /etc/systemd/system/mcs21-ops-monitor.service \
  /etc/systemd/system/mcs21-ops-monitor.timer \
  /etc/systemd/system/mcs21-audit-checkpoint.service \
  /etc/systemd/system/mcs21-audit-checkpoint.timer

# One manual, reviewed run each before scheduling.
sudo systemctl start mcs21-ops-monitor.service
sudo journalctl -u mcs21-ops-monitor.service -n 20 --no-pager
sudo systemctl start mcs21-audit-checkpoint.service
sudo journalctl -u mcs21-audit-checkpoint.service -n 20 --no-pager

sudo systemctl enable --now mcs21-ops-monitor.timer mcs21-audit-checkpoint.timer
systemctl list-timers mcs21-ops-monitor.timer mcs21-audit-checkpoint.timer --no-pager
```

Then download at least two external checkpoint objects to another machine and run the independent
verification above. Do not close #59 from a local-only checkpoint.

## 6. Incident runbooks

### A. Service outage / readiness failure

1. `systemctl status fyp-backend nginx mcs21-mysql --no-pager` and
   `curl -fsS http://127.0.0.1:8000/health/live`.
2. Read bounded journals (`-n 100`), never enable debug/request-body logging on the live service.
3. If DB readiness failed, verify MySQL health/TLS/disk before restarting anything.
4. If caused by a release, use `sudo mcs21-deploy rollback`; do not manually move the release
   symlink without the audited tool.
5. Preserve the monitor/deploy logs and record timestamps, release SHA, and corrective action.

### B. Storage corruption / integrity rejection

1. Do not overwrite or delete the suspect ciphertext. Record file UUID/object key only in a
   root-only incident note; do not paste the plaintext filename into shared logs.
2. Run the existing integrity/tamper diagnostics and compare `encrypted_sha256` to the stored
   object. A modified object must remain blocked from download.
3. Verify the newest same-host/offsite backup before restoring anything.
4. Restore only the affected object where possible, then re-run integrity verification.
5. If unexplained modification is confirmed, treat it as a security incident and preserve the
   external audit checkpoints from before and after the event.

### C. Suspected credential/token compromise

1. Revoke affected server sessions; if scope is unknown, revoke all sessions for the account.
2. Rotate the exposed operational credential (DB/email/S3/HMAC) at its provider. Do not log the
   replacement value.
3. If the checkpoint HMAC key may have been exposed, preserve all existing immutable checkpoints,
   rotate the key, and start a new documented key epoch; old checkpoints remain verified with the
   retired offline key.
4. Review auth rate-limit/fail2ban events and audit records using IDs/timestamps, not copied tokens.

### D. Failed migration / schema mismatch

1. Stop automatic deploys and keep the backend out of readiness.
2. Compare `/opt/mcs21/current/.mcs21-release`, Alembic head, and `audit_chain_heads.schema_revision`.
3. Use the reviewed migration/deployment procedure; never `stamp` or edit production metadata to
   silence readiness.
4. If code and schema cannot be made compatible immediately, roll code back to the compatible
   release. Database rollback requires the migration-specific reviewed procedure/backup, not an
   ad-hoc SQL edit.

### E. Audit-chain/checkpoint failure

1. Freeze deletion of external checkpoint objects and copy the affected series read-only to a
   separate machine.
2. Run `audit_checkpoint.py --verify` with the offline key. Distinguish: invalid HMAC, backward
   sequence, missing external objects, or mismatch between the current DB head and newest anchor.
3. Run the application's audit-chain verifier. Do not "repair" chain rows before evidence is
   captured.
4. A verified older external checkpoint is the lower bound of trusted history. Escalate any DB
   history that cannot be reconciled to it.

### F. Recovery-key incident

1. Disable/hold new recovery approvals if reviewer/recovery key custody may be compromised.
2. Never upload or email a recovery private key to diagnose the problem.
3. Review recovery audit records and redacted `recovery_operation` events for requester/reviewer
   separation and unexpected rejection spikes.
4. Replace the compromised recovery public-key registration through the reviewed recovery
   governance flow; retain the audit evidence and external checkpoints spanning the change.

## 7. Rollback / disable

Observability is non-authoritative: disabling it must not alter application data.

```bash
sudo systemctl disable --now mcs21-ops-monitor.timer mcs21-audit-checkpoint.timer
sudo systemctl stop mcs21-ops-monitor.service mcs21-audit-checkpoint.service || true
```

Reverting the application release removes the middleware/metrics endpoint. Existing external
checkpoints must **not** be deleted during rollback; they are historical evidence.

## 8. #59 staging evidence record

Do not mark #59 complete until these are filled with real host evidence:

| Item | Evidence |
|---|---|
| deployed merge SHA | `<pending>` |
| backend bound to loopback + trusted proxy restricted to 127.0.0.1 | `<pending>` |
| `/internal/metrics` reachable on backend loopback and not public through nginx | `<pending>` |
| monitor manual run / timer enabled | `<pending>` |
| deliberate monitor failure produced a redacted alert | `<pending>` |
| first external checkpoint destination/object | `<pending>` |
| independent second-machine HMAC verification | `<pending>` |
| log/alert secret-canary scan | `<pending>` |
