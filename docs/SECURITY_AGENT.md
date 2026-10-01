# Security Agent

[English](SECURITY_AGENT.md) | [简体中文](SECURITY_AGENT.zh-CN.md)

The supervisor's guidance for the AI Agent item was that an agent must **solve a specific automation
problem, not just add a chat box**: define its input data, its rules or model, its output format
and its boundaries, and demonstrate Critical / High / Medium / Low classification with a
Recommended Action. This is that definition and what was built (Admin → **Security agent**).

## The problem it automates

The platform already records a lot: a hash-chained audit log, integrity checks, file status,
recovery requests. No administrator will read thousands of rows to notice that one account has been
guessed at, that a session token was reused, or that a stored file changed. The agent reads that
evidence for them and answers one question: **of everything that happened, what is worth my
attention now, how urgent is it, and what should I do?**

## What it is, and is not

| It is | It is not |
|---|---|
| **Rule-based and deterministic.** Every finding comes from a named rule with a stated threshold. The same evidence gives the same report, each rule is unit-tested against fabricated events, and an administrator can read exactly why something was flagged. | A language model judging logs. No model is asked anything, so nothing is guessed and no log leaves the server. |
| **Read-only.** It never writes, never changes a file or an account, and cannot execute a recovery. A test fails if its modules gain a database write path or an audit-append. | Allowed to "fix" things. It recommends; an administrator acts. |
| **Metadata only.** It reads event type, time, count, account name, source address and file identifier. | Able to see file contents, keys, passphrases or ciphertext. The queries select named columns only, and a test pins that. |
| **Honest about its limits.** Every report says how much it read, and a clean report says it is not proof that nothing happened. | A claim that everything is safe. It sees only what the platform recorded. |

## Input data

| Source | What is read |
|---|---|
| `audit_logs` (window: last 24 h or 7 days; at most 5,000 newest events per type, and the report says when a type hit that cap) | `AUTH_LOGIN_FAILED`, `AUTH_REFRESH_REPLAY_DETECTED`, `FILE_DOWNLOAD_AUTHORIZED`, `FILE_SHARED`, `AUTH_PASSWORD_CHANGE_FAILED`, `RECOVERY_REQUEST_EXECUTED`: action, time, account name, source address |
| the audit hash chain | Recomputed in full (`AuditQueryService.verify_chain`): valid or not, and the first entry that fails |
| `integrity_checks` and `files` | Files that are `CORRUPTED` or whose newest check was `MODIFIED`, `MISSING` or `ERROR`, with each file's check history |
| `recovery_requests` | How many are still pending after 24 hours |
| integrity-scan coverage | When the last scan was recorded, how many files were never checked |

## Rules

| Rule | Watches | Raises |
|---|---|---|
| `INTEGRITY_DAMAGE` | Damaged stored files | **MODIFIED = Critical**, MISSING = High, ERROR = Medium |
| `AUDIT_CHAIN_BROKEN` | The audit hash chain | Any entry that does not verify = **Critical** |
| `SCAN_NOT_RUNNING` | When the last integrity scan ran | None in 36 h (or ever) while files exist = Medium |
| `LOGIN_GUESSING_SOURCE` | Failed sign-ins per source address, naming the accounts it tried | 10+ in 15 min = Medium, 30+ = High |
| `LOGIN_GUESSING_ACCOUNT` | Failed sign-ins against one account from **two or more** addresses | 10+ in 15 min = Medium |
| `SESSION_TOKEN_REUSE` | A used refresh token presented again | Any = High |
| `DOWNLOAD_BURST` | Downloads per account | 20+ in 10 min = Medium, 60+ = High |
| `SHARE_BURST` | Shares per account | 10+ in an hour = Low |
| `PASSWORD_CHANGE_GUESSING` | Failed password changes per account | 5+ in 15 min = Medium |
| `RECOVERY_EXECUTED` | Executed recoveries, requests waiting over a day | Executed = Medium, waiting = Low |

One address guessing at one account is one incident and is reported once, by the source rule,
with the account named in its evidence; the account rule is for guessing spread across addresses,
which the per-address view splits into pieces too small to notice.

Bursts are measured with a sliding window: 40 failures spread over a day are not a burst; 10 in
five minutes are. The thresholds are constants at the top of
`backend/app/services/security_agent_rules.py`; changing one is a reviewed code change, and the
report states them.

Priority means: **Critical** act now, **High** act today, **Medium** look into it this week,
**Low** when convenient.

## Output format

`GET /api/v1/admin/agent/report?window_hours=24|168` (administrators only) returns, and the page shows:

```
generated_at, window_hours
counts:      critical / high / medium / low
findings[]:  rule_id, priority, title, summary,
             evidence[]            (why it was flagged: counts, accounts, addresses, times),
             recommended_action    (what to do),
             file_id?              (for file findings)
rules[]:     every rule, what it watches, its threshold, how many findings it raised this time
inputs:      audit events read, audit-chain entries verified, files checkable / never checked, last scan
boundaries[] what the agent will not do
```

## Recovery guidance for damaged files

For a damaged file the recommended action names the exact command (`scripts/restore_file.py --file-id
… `, always the dry run) and **which backup sets can hold the original**, worked out from the
file's own check history: sets taken between the upload and the last passing check *certainly* hold
it; sets up to when the damage was first seen *probably* do; a later set may already hold the damaged
bytes. `restore_file.py` checks the SHA-256 and refuses a set that does not match. This ties the agent
to the recovery flow in [BACKUP_AND_RECOVERY.md §9](BACKUP_AND_RECOVERY.md#9-finding-and-restoring-one-damaged-file)
without the agent being able to run it.

## Demonstration (with real events, nothing fabricated)

The audit log is append-only and hash-chained, so there is no way to inject fake events, and none is
wanted. To show each class:

1. **Medium, password guessing:** send ten wrong passwords for one account. The sign-in throttle
   answers 429 after ten, and all ten are in the audit log, so the report shows
   `LOGIN_GUESSING_SOURCE` and `LOGIN_GUESSING_ACCOUNT`.
2. **Critical, tampered file:** in the tamper lab (`security-lab/run.sh`) or a disposable stack,
   flip a byte of a stored object and press **Scan now** on the Integrity tab, then open **Security agent**:
   `INTEGRITY_DAMAGE` with the backup window and the restore command.
3. **High, missing object:** move an object out of storage and scan: `INTEGRITY_DAMAGE` as High,
   described as a storage problem, not tampering.
4. **Medium, detection not running:** on a deployment whose timer has not run in 36 hours.

## Tests

- `tests/unit/test_security_agent_rules.py`: each rule's thresholds, grading, attribution to the
  right source and account, ordering, determinism, the backup-window text, and that only the dry
  run is ever suggested.
- `tests/unit/test_security_agent_service.py`: the window, which events are requested, how a check
  history becomes "last intact" and "damage first seen", admin-only access, the SQL selects named
  columns only, and the modules have no write path.
- `frontend/src/e2e/live-stack.integration.test.ts` (CI `e2e-live`): ten real failed sign-ins against the running API become one ranked `LOGIN_GUESSING_SOURCE` finding with evidence and an action; an ordinary user is refused.
- `tests/integration/test_security_agent_mysql.py`: on real MySQL, a really tampered file is reported
  as Critical with its backup window, and every query runs.
- `frontend/src/utils/agent-report.test.ts`: how findings are presented.

## Limits, and what comes next

- It sees only what is recorded. An attack that left no audit event is invisible to it.
- Source addresses behind a proxy are as good as the proxy headers the API trusts.
- There is no stored history of reports and no notification: it answers when asked. A natural next step
  is to run it daily and send the Critical/High findings through the existing failure-alert mail.
- **A language-model layer is deliberately not part of v1.** Its only plausible job would be rewording
  a finding for a non-technical reader, and that would send audit metadata (account names, addresses)
  to a third party. If it is ever added it should be optional, off by default, fed only the already
  redacted finding text, and never allowed to change a priority or take an action.
