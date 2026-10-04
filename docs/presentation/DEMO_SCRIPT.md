# Four-minute live demo script

[简体中文](DEMO_SCRIPT.zh-CN.md)

The demo slot is 3:30–7:30 of the 12-minute presentation ([TALKING_POINTS.md](TALKING_POINTS.md) §0).
It shows the three claims the audience should leave with: the file is encrypted before it leaves
the browser, only the named person can open it, and a changed file is refused. Everything runs on
staging, `https://secureview.tech`.

## Cast and setup

| Who | Where | Signed in as |
| --- | --- | --- |
| Presenter ("Alice") | Browser window A, left half of the screen | `demo-alice` |
| The colleague ("Bob") | Browser window B, right half, **a separate browser profile** so the two sessions do not share storage | `demo-bob` |
| The attacker | A terminal, minimised until step 4 | root on the VPS |

`demo-alice` and `demo-bob` already exist on staging (seeded 2026-10-04, so no email code is needed;
login password `mcs21666`, passphrases kept by the project owner). The names must start with `demo-`,
because the tamper tool refuses any other account. Use passphrases that differ from each other and
from any real account.

Before the presentation, as `demo-alice`, upload `quarterly-results.txt` (a short readable text file)
and share it with `demo-bob`. This pre-shared file is the one tampered with in step 4, so its id
can be looked up in advance; the file uploaded live in step 1 is new and its id is not known yet.

## The script

| Time | Step | Do | Say |
| --- | --- | --- | --- |
| 0:00–0:15 | Set the scene | Point at the two windows | "Alice wants to send Bob a confidential report. Neither of them trusts the server, and neither should you." |
| 0:15–1:15 | **1. Upload** | In A: Upload → choose `board-minutes.pdf` → Start Encryption. Let the steps play | "Every step you see is timed for real: encrypt in the browser with a fresh key, wrap that key, upload. Look at the bytes: the file starts `%PDF`; what the server receives is noise." |
| 1:15–2:05 | **2. Share** | In A: My Files → `board-minutes.pdf` → Share → type `demo-bob` → Share. The confirmation shows Bob's key fingerprint. In B: Settings shows the same fingerprint | "Before anything is sent, Alice sees which key the file will be locked to. Bob reads his fingerprint from his own Settings: they match, so only Bob can open it. The server never had the key." Then Confirm and share |
| 2:05–2:45 | **3. Open** | In B: My Files → Shared with me → `board-minutes.pdf` → Download. Open the saved file | "Bob unlocks with his own passphrase, never Alice's. The file is checked on the way out, then decrypted on his device." |
| 2:45–3:40 | **4. Tamper** | Bring up the terminal; run `flip` from [TAMPER_DEMO.md](TAMPER_DEMO.md) on `quarterly-results.txt`. In B: Download that file | "Now I am the server's administrator, or someone who broke in. I change one byte of a stored file." The download is refused and the row turns **Modified**. "Changed, so refused. Nobody was asked to trust us." |
| 3:40–4:00 | Close | Back to the slides | "Encrypted before it leaves the device, opened only by the named person, refused if changed." |

Straight after the talk, run `restore` (TAMPER_DEMO.md) and click the file's status badge as
`demo-alice` so it reads Verified again.

## The day before

- [ ] Both demo accounts sign in on staging, and `quarterly-results.txt` is shared from Alice to Bob.
- [ ] `demo_tamper.py list --owner demo-alice` shows the file and nothing marked TAMPERED; the
      `flip` and `restore` commands are written out with the file id, ready to paste.
- [ ] One full rehearsal, timed, ending with `restore`.
- [ ] The backup video is recorded (below) and copied to the presentation laptop.
- [ ] Nothing is merged to `main` from two hours before the talk. A merge triggers the automatic
      deploy, which restarts the service for a few seconds.

## 30 minutes before

- [ ] Health check: `https://secureview.tech/health/live` returns 200.
- [ ] Both windows signed in and **already unlocked** (open one file in each), so the audience does
      not wait for the passphrase key derivation.
- [ ] Browser zoom 125 %, notifications and chat apps off, password-manager pop-ups dismissed.
- [ ] `board-minutes.pdf` sits on the desktop; delete any earlier copy from Alice's My Files.
- [ ] Phone hotspot ready in case the venue network fails.

## If something goes wrong

| Problem | Do |
| --- | --- |
| The network drops or staging does not answer | Switch to the backup video at the same step; it follows this script |
| Unlock or a download hangs for more than ~10 s | Say "this is where it would…", switch to the video for that step |
| The tamper download unexpectedly succeeds | `list`: if the file is not marked TAMPERED, the `flip` did not run; show the video's step 4 |
| A step was mis-clicked | Do not repair it live; go to the next step |

## The backup video

Record the whole script once on staging with the same accounts, using the screen recorder of the
presentation laptop (on macOS, QuickTime → New Screen Recording), full screen at the same zoom. Keep
it about four minutes, with no sound, so the presenter can talk over it. Check it plays from the
laptop without a network. Do not commit it to the repository; it shows the real staging site.
