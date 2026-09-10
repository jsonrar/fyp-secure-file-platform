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

## What it does not cover

The browser interface itself. This drives the same modules the pages call, so it proves the
logic and the API contract, not the markup — a button wired to the wrong handler would pass
here. The dialogs and lists are checked separately against a stand-in API.
