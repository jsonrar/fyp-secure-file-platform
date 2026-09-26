# End-to-end verification

`frontend/src/crypto/mvp.integration.test.ts` exercises the product the way a user does —
real crypto in the client, a real backend over HTTP, two real accounts — and asserts the
things unit tests cannot reach.

It is skipped unless the environment names a backend and two accounts, so `npm test` stays
offline and deterministic.

## What it proves

| Step | The claim being tested |
| --- | --- |
| Sign in | A session carries both tokens, so it can be renewed rather than dying at 30 minutes |
| Upload | The metadata envelope is one the API actually accepts, and every file is wrapped to the recovery key as well as the owner's |
| List | The file is reported as owned, and names its owner |
| Download | The bytes that went in come back out, from what the server stores plus the passphrase |
| Share | The file key is rewrapped to the recipient, resolved by username or email |
| Shared users | The recipient holds `can_download` but not `can_share`, and is not the owner |
| Recipient's list | The same file is reported as **not** owned, and names the sender |
| Recipient's download | **They decrypt with their own passphrase** — the promise the proposal makes in as many words |
| Cross-account refusal | The sender's passphrase does not open the recipient's account key |
| Audit trail | The owner sees the recipient's download, with a name and a time on every row |
| Revoke | The grant is withdrawn |
| After revoke | The file leaves the recipient's list, and a direct request is refused as a uniform 404 |
| Owner unaffected | Revoking someone else does not cost the owner their own access |

The two accounts must have **different encryption passphrases**. With the same passphrase
the most important assertion — that the recipient decrypted with their own key and not the
sender's — cannot be distinguished from the alternative, and quietly proves nothing. The
first run of this suite had exactly that flaw.

## Running it

Seed two accounts on the target deployment:

```bash
cd backend
set -a && . /etc/fyp-secure-file-platform/backend.env && set +a
PYTHONPATH=$PWD .venv/bin/python scripts/seed_test_account.py \
  --username e2e-sender --email e2e-sender@secureview.tech \
  --password '<password>' --passphrase '<one passphrase>'
PYTHONPATH=$PWD .venv/bin/python scripts/seed_test_account.py \
  --username e2e-recipient --email e2e-recipient@secureview.tech \
  --password '<password>' --passphrase '<a different passphrase>'
```

Then, from `frontend/`:

```bash
E2E_API_BASE=https://secureview.tech/api/v1 \
E2E_SENDER=e2e-sender E2E_SENDER_PASSWORD='...' E2E_SENDER_PASSPHRASE='...' \
E2E_RECIPIENT=e2e-recipient E2E_RECIPIENT_PASSWORD='...' E2E_RECIPIENT_PASSPHRASE='...' \
npx vitest run src/crypto/mvp.integration.test.ts
```

The suite uploads one file and deletes it again on the way out, so a run leaves the
deployment as it found it.

## The disposable stack: every live suite, un-skipped, in CI

Four frontend suites talk to a real backend, and each skips itself without its environment:
`crypto/mvp`, `crypto/upload`, `crypto/passphrase-reset`, and `e2e/live-stack`. The `e2e-live`
CI job runs all of them against a fresh API process and a disposable MySQL 8.4, then fails if
the JUnit report contains a single skipped test (`backend/scripts/check_no_skips.py`).

`backend/tests/e2e/run_live_stack.sh` does the work, so the same run is one command locally:

```bash
DB_HOST=127.0.0.1 DB_PORT=3310 DB_USER=... DB_PASSWORD=... DB_NAME=fyp_local_test \
  bash backend/tests/e2e/run_live_stack.sh      # add E2E_COVERAGE=1 for coverage
```

It migrates the schema, seeds the sender, recipient and passphrase-reset accounts with
`seed_test_account.py` (distinct random passphrases, `@example.com` addresses), promotes a
fresh admin, starts `backend/tests/e2e/live_server.py serve`, registers a recovery key through
the admin route, runs vitest, and removes every key, mailbox message and uploaded object on
exit. The database name must carry a `_test` segment or the server refuses to start.

`live_server.py` is the unmodified `create_app()` with one substitution: verification mail is
written to a directory instead of being sent, so `e2e/live-stack` can complete a real
registration. The `console` email provider would print the code into the server log, which CI
keeps.

`e2e/live-stack.integration.test.ts` needs no seeded users. It covers:

| Area | What is asserted |
| --- | --- |
| Registration and verification | A wrong code is refused and creates nothing; the emailed code registers; a taken username is a 409 |
| Login | Wrong password and unknown account are indistinguishable 401s |
| Refresh | Rotation retires the old access token; replaying a consumed refresh token revokes the whole family, including the tokens just issued |
| Logout | Both the access and the refresh token stop working |
| Unlock | Another account's passphrase is refused; the right one opens the key |
| File algorithms | AES-128/192/256-GCM and ChaCha20-Poly1305 each round-trip binary content, report the right algorithm, and serve ciphertext only |
| Share and revoke | The recipient decrypts with their own passphrase, cannot re-share, and after revocation gets a uniform 404 on read and download |
| Audit visibility | The owner sees the recipient's download; the recipient sees only rows about themselves |
| Role denial | Anonymous callers get 401; an ordinary user gets 403 on admin, chain-verification and recovery-key routes; the admin gets in and the chain verifies |
| Account deletion | A wrong password leaves the account intact; deletion ends sessions and sign-in, destroys owned files, and leaves a valid audit chain |

### The browser smoke test

The Node suites run the browser's own code — the API clients, the WebCrypto and Argon2 key
handling, the upload, download and share modules — over real HTTP, which is where the security
properties live. What they cannot see is the markup: a button wired to the wrong handler passes
every one of them. `frontend/browser-tests/golden-path.browser.ts` closes that gap. Chromium,
driven by Playwright, clicks the built pages through the golden path:

| Step | How it is driven |
| --- | --- |
| Register two accounts | The register form, with **Send code** |
| Email verification | The code is read from the stack's mailbox directory (the same one `e2e/live-stack` reads) and typed into the form; nothing is sent |
| Sign in | The login form |
| Upload | The file picker and **Start Encryption** on `/upload` |
| Unlock the key vault | The passphrase dialog raised by **Download and decrypt** |
| Download | The browser's own download, compared byte for byte with the original |
| Share | The row's **Share** button and the share dialog |
| Recipient sees it | The second account's **Shared with me** list, then a download decrypted with its own passphrase |
| Revoke | **Revoke** in the share dialog, then **Revoke access** on the confirmation |
| Recipient no longer sees it | The recipient's list after a reload |
| Log out | **Log out** in the account menu; a protected page then sends the browser back to sign in |

Every step is driven through the UI; none is done over the API. The UI's **Log out** calls
`POST /auth/logout` to revoke the server session family, then clears the browser tokens and
unlocked key. The test asserts what the button does — tokens gone, protected pages redirect —
and does not separately re-check the server-side revocation (that contract remains covered by
`e2e/live-stack`).

Selectors are roles, labels and visible text only; no `data-testid` was needed. There are no
sleeps: every wait is a Playwright web-first assertion, and the mailbox is polled with
`expect.poll`. It runs with one worker, no retries, and `failOnFlakyTests`, so a test that only
passes on a second attempt fails the run.

#### Running it locally

Prerequisites: the backend venv, `npm ci` in `frontend/`, a disposable MySQL 8.4 database whose
name has a `_test` segment, and Chromium for Playwright (once):

```bash
cd frontend && npx playwright install chromium   # add --with-deps on a fresh Linux host
```

Then, from the repository root:

```bash
# The Node live suites, then the browser test, against one stack
E2E_BROWSER=1 DB_HOST=127.0.0.1 DB_PORT=3310 DB_USER=... DB_PASSWORD=... DB_NAME=fyp_local_test \
  bash backend/tests/e2e/run_live_stack.sh

# Only the browser test (the stack is still migrated, seeded and torn down)
E2E_BROWSER=only DB_HOST=... bash backend/tests/e2e/run_live_stack.sh
```

The script builds the frontend with `VITE_API_BASE_URL` pointed at the disposable API, and
Playwright serves that build with `vite preview` on `127.0.0.1:5173` — the production bundle, not
the dev server, and an origin the API already allows by default. Ports 8000 and 5173 must be
free. Results land in `E2E_BROWSER_REPORT_DIR` (default `./e2e-browser-reports`): `junit.xml`,
and `html/` (`npx playwright show-report e2e-browser-reports/html`). Each run registers new
accounts, and the verification-code limit is 20 sends per IP per window, so for many repeated
runs recreate the database in between.

#### What CI keeps, and what it never records

In CI the test runs inside the `e2e-live` job right after the Node suites, against the same
stack. Only Chromium is installed (`npx playwright install --with-deps chromium`), and the
browser download is cached under a key holding the exact Playwright version.

**Traces are never recorded in CI.** A Playwright trace keeps every request header and body,
DOM snapshots and typed values: bearer tokens, the private key the register page shows once,
wrapped key material. Locally a failed run keeps one (`retain-on-failure`) for debugging; it never
leaves the machine.

The HTML report is uploaded only when the job fails, and only after
`backend/scripts/check_report_hygiene.py` passes it. The report does contain the values the test
typed — usernames, `@example.com` addresses, passwords and passphrases — because Playwright's step
titles include them; every one of those is minted by the test for a throwaway account in a
database destroyed with the job (`Throwaway!<uuid>` passwords, `throwaway … passphrase <uuid>`
passphrases), and the uploaded file is random bytes. The test never prints file bytes. Failure
screenshots are taken by the test itself with the private-key box masked. The hygiene script
unpacks ZIP attachments and the report's embedded base64 results (a byte-level scan cannot read
either), and refuses any Playwright trace outright, so a report with a trace can never be
published even if someone turns tracing on.

## Backend concurrency and fault injection

`backend/tests/integration/test_concurrency_mysql.py` races real threads, each on its own MySQL
connection, released together by a barrier: session limits, the login-failure counter, refresh
token reuse, the audit hash chain (with writers that roll back mid-transaction), racing key
rewraps, duplicate shares, a share racing a delete, duplicate recovery requests, and a recovery
execution racing a revocation. Every one of them was checked by removing the row locks it
depends on and confirming the test then fails.

`backend/tests/integration/test_fault_injection_mysql.py` produces each failure with the
mechanism that would really cause it: the server kills the connection at COMMIT after the
ciphertext is published (and `scripts/reconcile.py` then removes the orphan), the object store
refuses a publish or an unlink, envelopes arrive truncated or naming the wrong keys, and
signatures are forged, made by the wrong key, or cover a different payload.

Both run in the `mysql-gate` job with the rest of the integration suite.

## What it does not cover

The browser smoke test walks one path in one browser (Chromium) at one viewport. It does not
cover every page, error state, the mobile layout, Firefox or WebKit, or visual regressions; the
Node suites cover the edge cases of each flow, and the smoke test only proves the pages are wired
to them.
