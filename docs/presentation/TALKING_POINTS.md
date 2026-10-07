# Presentation talking points (kept up to date)

[English](TALKING_POINTS.md) | [简体中文](TALKING_POINTS.zh-CN.md)

Material for the report, the Final Presentation slides and the live pitch. Each point says **what to
say**, **where the numbers and evidence are**, **what a judge is likely to ask** and **how to answer**.
Anything marked *planned* or *in review* is not done yet; do not present it as done. What is still
missing, and in what order to fix it, is in [REFLECTION.md](REFLECTION.md).

Last updated: 2026-10-07

---

## 0. The 12 minutes

The unit's guidance (Ed #66) is that the presentation is about outcomes and deliverables, with **no
project-management content**. Time follows its nine parts:

| Time | Content | Uses point |
| --- | --- | --- |
| 0:00–1:00 | Opening and the problem: an ordinary cloud drive can read your files, and a breach exposes all of them | — |
| 1:00–1:45 | Target users and a one-slide requirements status table | `docs/PROPOSAL_TRACEABILITY.md` |
| 1:45–3:30 | Design: architecture diagram and encryption flow | 1 |
| 3:30–7:30 | **4-minute live demo**: (1) upload, showing the encryption steps and the byte comparison; (2) share, and the recipient downloads and decrypts; (3) change the stored ciphertext on the server, and the recipient's download fails ([TAMPER_DEMO.md](TAMPER_DEMO.md)) | 1, 2 |
| 7:30–9:30 | Outcomes and evidence: load-test numbers, the bug testing found and fixed, the alert emails | 3, 4, 5 |
| 9:30–10:30 | Limitations, raised by us | 7, 8 and REFLECTION |
| 10:30–12:00 | Future work, conclusion, buffer | REFLECTION |

## 1. End-to-end encryption: the server never touches plaintext

**What to say:** files are encrypted in the user's own browser under a fresh random key per file. That
file key is wrapped with RSA-OAEP to the user's public key and to the recovery key. The server receives
only ciphertext, wrapped keys and metadata, and has no way to decrypt.

**Evidence:**
- `docs/ENCRYPTION_EVIDENCE.md`, `docs/crypto/FILE_ENVELOPE.md` (the format and test vectors)
- The `tamper-drill` CI job: stored ciphertext is altered on the server and the client must detect it
- The live tamper demonstration, [TAMPER_DEMO.md](TAMPER_DEMO.md): one byte of the stored file is changed
  on staging in front of the audience and the recipient's download is refused. Rewriting the database
  digest as well is still refused, because the upload's digest is also in the hash-chained audit log
- The ciphertext preview panel on My Files
- The encryption steps shown during upload (point 2)

**Likely question:** what can the server actually see?
**Answer:** metadata such as file name, size, MIME type and timestamps, which the file list and sharing
need; never the contents or the file key. Saying this plainly is more credible than "the server sees nothing".

## 2. "It uploaded instantly — was it even encrypted?" The encryption steps on upload (PR #156)

**Background:** AES-GCM in the browser is hardware-accelerated, so encrypting a few MB takes tens of
milliseconds. Pressing the button used to finish at once and looked as if nothing had happened.

**What we did:** the upload now shows the real pipeline: read the file → encrypt with the chosen
algorithm (fresh key and nonce, then decrypted once to check it) → wrap the file key with RSA-OAEP →
upload the ciphertext only (with a real progress bar). Each step shows its **measured** time. Then the
file's first 16 bytes are shown **beside** the first 16 bytes of ciphertext: a PDF starts `%PDF-1.7`,
and what the server receives is random bytes. Measured locally on a 3 MB file: 21 ms to encrypt and
self-check.

**How to say it:** "We don't slow anything down to look convincing. Every time shown is measured, and
the before/after bytes are the evidence." Each step stays on screen at least 0.35 s so people can read
it; the times shown exclude that pause.

**Likely question:** is the animation just an effect?
**Answer:** the bytes are the real start of this upload's plaintext and ciphertext, and the times are
measured by the code around each step. The flip is only how the final value appears; the value is real.

## 3. Capacity measured, not claimed (#140, PR #155)

**What to say:** at the 2026-10-01 meeting the supervisor asked for numbers instead of "it supports many
users". We wrote a load tool that encrypts exactly like the browser and ran the full matrix on staging
on the night of 2026-10-03/04.

**Fix verified on staging (2026-10-04 evening):** at 100 concurrent users, uploads went from 78 % failed
(HTTP 500) to **102 of 102 succeeded**, with 0 integrity failures on 102 decrypted downloads
([evidence](../performance/pool-fix-2026-10-04/README.md)).

**Key numbers:**
- 22,264 operations; 5,094 downloads decrypted and SHA-256-compared with the original, **0 integrity failures**
- pdf/png/jpg/mp4/zip/exe from 1 MB to 500 MB all round-trip byte-exact (144/144)
- 5 users on a mixed load for 108 minutes in total (19,372 operations) with no server error; no server
  error up to 50 concurrent users
- At 100 concurrent users errors begin (65–78 % of uploads get HTTP 500), because the 15-connection
  database pool is exhausted while CPU averages 3 %: **the limit is not the hardware**
- When the load drops, the service recovers to zero errors by itself, with no restart
- Simultaneous sign-ins: by design the server verifies two passwords at a time (Argon2id is
  memory-hard); extra requests get an immediate 429 to retry, and nothing crashes

**Evidence:** `docs/performance/REPORT-2026-10-03.md` (with charts), the conclusions at the end of
`docs/PERFORMANCE_TESTING.md`, raw data in `docs/performance/raw/`, the server sampler CSV.

**Conditions you must state:** the generator was a laptop on a home connection, so every transfer
figure is bounded by that link (~24 Mbit/s up, ~13 Mbit/s down); the server's own port is ~100 Mbit/s.
The report's "Test conditions" section says so.

**Likely question:** why does 500 MB take minutes?
**Answer:** that is the test link's bandwidth, not the server. Server CPU stayed low throughout; its
port tops out at about 100 Mbit/s, which still means 40-plus seconds for 500 MB.

**Likely question:** it fails at 100 users?
**Answer:** it did, and then we fixed it. The test pointed at the database pool, not the hardware.
Our first guess, that file transfers held connections, was **wrong**, and a measurement showed it: slow
downloads held no transaction. The real cause was uploads holding a connection while waiting for a thread
pool whose threads were all waiting for connections. After the fix (PR #163), the same tool on the same
machine at 100 users: **80 % of uploads failed → 0 %, 0.33 → 56 operations per second**. Show the two
charts in `docs/performance/pool-fix-2026-10-04/` side by side. The same 100-user step was then re-run on
staging (2026-10-04 evening): 102 of 102 uploads and 102 of 102 verified downloads succeeded
([staging re-run](../performance/pool-fix-2026-10-04/staging-rerun/REPORT.md), #172).

**How to tell it:** this is the strongest engineering story in the project: measure, find the bottleneck,
be wrong once and prove it, fix the real cause, measure again.

## 4. Testing found real bugs, and they were fixed (#139 → PR #154)

**What to say:** the load tool's local dry run found two MySQL deadlocks that only appear under
concurrency: two new accounts signing in at the same moment, and a download racing a share. Users saw
HTTP 500.

**Fix:** as MySQL recommends, a deadlock (1213) or lock-wait timeout (1205) rolls back and retries the
whole transaction, up to three times.

**Evidence:**
- A new regression test reproduced the deadlock about 7 times in 10 before the fix, and never after
- All 627 backend tests passed at the fix, 85.17 % coverage; on 2026-10-07 (CI on `e4b3f13`) the full
  MySQL suite is 632 tests at 85.27 % branch coverage, alongside 866 frontend live tests and 57 browser specs
- 28,540 requests on staging that night, not one deadlock

**How to say it:** "Our testing wasn't a formality: it found a real concurrency bug before users did, we
fixed it, and the tests prove the fix."

## 5. Monitoring really does alert

**What to say:** `mcs21-observe` checks error counts, sign-in throttling, disk, and the audit-chain
checkpoint every five minutes and emails when a threshold is crossed. On the test night, each of the
three deliberate overloads produced one alert email (22:25, 00:45, 02:45), each cleared on the next check.

**Evidence:** screenshots of the alert emails, `docs/OBSERVABILITY_AND_INCIDENT_RESPONSE.md`, the
Monitoring line in the load-test report summary.

## 6. Engineering quality of the test itself

Per Ed #66, **do not present this as project management**: it is the engineering reason the numbers can
be trusted.

- Backups, reconciliation, the integrity sweep, the security agent and auto-deploy were paused during
  the run so they could not distort the numbers
- One minimal SSH port exception was opened for the test and removed afterwards
- Every test account and file was deleted through the API afterwards, disk returned to its baseline,
  and the backup was run again
- Failures caused by the generator's own side (the home network dropping, the SSH tunnel) are reported
  separately and not counted as server errors

**How to say it:** "We can account for every failure, which is why these numbers can be trusted."

## 7. Stopping mass uploads from taking the server down

**Controls that already existed:**
- Only accounts registered with an emailed verification code can upload; registration and code sending
  are rate-limited
- nginx limits each IP: 10 API requests per second (burst 20), 12 sign-ins per minute
- 500 MB per file; nginx receives the whole upload before passing it on, so slow clients cannot tie up the backend
- Disk above 85 % and error bursts email an alert; the security agent detects password guessing,
  download bursts and share bursts

**The gap that existed:** recorded in the threat model (`docs/THREAT_MODEL.md` T-D2 / F-09): no
per-account storage quota, so one account could in principle fill the disk.

**The hardening (PR #157, merged and deployed):**
1. Each account may store 2 GB and upload 5 GB per 24 hours (deleted files count), with a clear message
   when exceeded; all uploads are refused when free disk would fall below a floor
2. nginx allows 10 uploads in flight per IP (not lower, because a campus network puts many people behind one address)
3. A new `UPLOAD_BURST` rule in the security agent
4. A warning before downloading a program or macro-capable file someone shared (.exe, .bat, .js, .docm, …)

**Be honest about large DDoS:** that cannot be stopped in the application, and a 100 Mbit/s port is
easy to saturate. A real deployment would sit behind a service such as Cloudflare. Calling it a known
risk outside this project's scope is more professional than pretending to stop it.

**How to say it:** "We threat-modelled first, knew where the gaps were, ranked them by risk, and closed them one by one."

## 8. Why we don't scan for viruses: the zero-knowledge trade-off

**What to say:** the server only ever has ciphertext; antivirus on it would scan random bytes. Server-side
scanning is impossible by construction of end-to-end encryption, not an oversight; other end-to-end
encrypted drives (Proton Drive, for example) cannot scan contents on the server either.

**How we compensate:**
- Files can only be shared with registered users the uploader names; there are no public links, so the
  risk is that of an email attachment from someone you know
- Once decrypted in the browser and saved, the file is scanned by the operating system's own antivirus
  (Windows Defender, macOS XProtect) as usual
- A warning before downloading a program or macro-capable file (PR #157)
- We **deliberately do not** send file hashes to a service such as VirusTotal, which would tell a third
  party who holds which file

**How to say it:** "Privacy and server-side scanning cannot both be had. We chose privacy, and reduce the
risk with sharing scope, a download warning and endpoint antivirus."

## 9. Checking who a file is really shared with: key fingerprints (PR #160)

**What to say:** a server that could swap a recipient's public key for its own would receive every
file shared to that person. Our threat model listed this (T-S5) and recommended a control; we built
it. Before anything is shared, the dialog names the recipient and shows the fingerprint of the key the
file will be sealed to, **computed in the browser** from the key itself, never taken from the server.
The recipient sees the same fingerprint in their Settings, so two people can read it out and compare.
The browser remembers each recipient's fingerprint and warns if it changes later, the same idea as
SSH's known hosts or Signal's safety numbers. The key that was confirmed is exactly the key used:
there is no second lookup in between.

**Demo it:** share a file, point at the fingerprint, then open the recipient's Settings on the second
screen and show that it matches.

**Likely question:** does this stop every attack?
**Answer:** no, and we say so. It stops a server-side data attacker from silently redirecting a share.
Someone who controls the code the browser runs could remove the check (threat model N1), and the very
first share on a new device trusts the first key it sees. The comparison is the user's choice.

---

## 10. Usability (NFR2): real use, but no formal study

**Status:** the supervisor, the four team members, the FIT3162 Teaching Team and other students have
used the live site with their own accounts for the core flows (register, encrypt and upload, share,
open, revoke). The formal study we had planned (task cards, SUS questionnaire, pass criteria fixed in advance) was
**not run**, and its materials were deleted on 2026-10-05; #115 was closed as not planned. So there is no SUS score and no per-task completion rate.

**What to say:** "NFR2 is supported by real use rather than a formal study. Our supervisor, the
Teaching Team and other students have used the live site with their own accounts. We also did a
first-time-user walkthrough, and it changed the product: two-step registration, labelled file actions,
a getting-started checklist, and confirming who you share with. We had considered a formal study but chose not to run it, so we do not quote
a usability score."

**Do not say:** "a usability study showed…", "users rated it…", or any SUS number or completion
rate. Do not invent how many people used it: say who, not a count we did not measure.

**Likely question:** so how do you know non-experts can use it?
**Answer:** people without a cryptography background (classmates, the Teaching Team) have used it on
the live site with their own accounts, and our own first-time-user walkthrough changed four things
where a new user would get stuck. It is real but informal evidence; the planned study with pass criteria is in the repository if
someone wants to run it.

## 11. We audited our own interface with a script, not by eye (#183)

**What happened:** after the "Sealed" restyle the pages looked fine one at a time and wrong together
(headings left or centred, widths all different, the sidebar disappearing on Help). We wrote
`frontend/scripts/layout-audit.mjs`: it opens every page in five configurations (1440 light, 1440 dark,
768, 390 phone, 1440 Chinese), takes full-page screenshots and measures squeezed headings, horizontal
overflow, clipped text, small tap targets, untranslated English and console or HTTP errors.

**What to say:** "We do not judge the interface by eye. One script measures about a hundred page views
and gives numbers, and a change is not finished until squeezed headings and overflow are zero." Say what it
**cannot** do: it measures layout, it does not decide whether a page is good.

**A colour rule the audit checks:** green means only "verified" or "sealed", red only "changed" or "dangerous". In dark mode the primary buttons are near-white, and a scan of every control on every page found none in the success green (#184).
**A real find:** the audit's console column showed that every visit to Access Records made a request the user was not allowed to make (a 403 on the chain check) and one failing request per deleted file (404). The fix sends file names with the audit rows and runs the chain check only for administrators; the same script now reports zero errors on all 100 page views (#185).

**Not everything is measurable:** the script cannot see that a table's question column reads as a third answer, or that a footer has an empty column; those came from looking at the page as a visitor would and were fixed by hand ([PR #194](https://github.com/jsonrar/fyp-secure-file-platform/pull/194)). Say both: numbers for layout, eyes for meaning.

**Then we turned the eye-findings into a second script:** after the third "this heading wraps badly" from the project lead, `frontend/scripts/text-audit.mjs` measures every heading and short paragraph at six widths in both languages for capped text, sentences broken mid-way, two-sentence headings and lonely last words. Two-sentence intros now break only at the full stop (a `SentenceLines` component), in Chinese too ([PR #195](https://github.com/jsonrar/fyp-secure-file-platform/pull/195)). Good answer to "how do you keep the UI consistent?": a rule, a component that enforces it, and a script that checks it.

**Do not say:** that this replaces usability testing (see §10).

## 12. The file details panel: the evidence one click from the list ([PR #193](https://github.com/jsonrar/fyp-secure-file-platform/pull/193))

**What it shows:** click any row in My Files and a panel opens beside the list with the cipher, the exact
original and stored sizes, the ciphertext SHA-256 recorded at upload, who can open the file (and that the
recovery key can too), and every action. Click another row and the panel switches; nothing is dimmed.

**What to say:** "The list tells you a file is Verified; one click shows you why: the fingerprint every
download and the nightly scan are checked against, and exactly who holds a key." In the demo, open the
panel on the file you just shared to show the recipient listed with "can open".

**If asked why not a pop-up:** it describes one row and the list is its context, so it sits beside the
list and is not modal; pop-ups are kept for steps that need an answer (unlock, confirm share). On a phone
it becomes a bottom sheet.

**Do not say:** that the panel checks integrity by itself. The Verified badge reflects the last check;
"Check integrity" runs a new one.

## 13. An administrator can reset a password but can never see one ([PR #197](https://github.com/jsonrar/fyp-secure-file-platform/pull/197))

**What it shows:** Admin → Users → Details shows an account's email, status, sign-in times and counts.
"Reset login password" gives a random temporary password, shown once, signs the account out everywhere
and emails the holder, who then picks their own in Settings.

**What to say:** "Our administrators cannot read passwords, because there is nothing to read. The login
password is stored as a one-way hash, and the encryption passphrase never reaches the server. So the
admin can get someone back into their account, but cannot get into their files: a reset changes only the
login password, and the files still open only with the passphrase."

**If asked "why not just show the admin the password?":** storing passwords so they can be shown means a
database leak exposes every password; a security product that did this would fail its own threat model.

**Evidence:** the reset is audited as `ADMIN_PASSWORD_RESET` without the password; tests check that only a
hash is stored, sessions are revoked, and that admins cannot reset themselves or other admins.

## Quick answers for judges

| Question | One-line answer | See |
| --- | --- | --- |
| Is it really encrypted? | The upload shows each step's measured time and the bytes before and after; the live tamper demo shows a changed byte being refused; CI also runs a tamper drill | 1, 2 |
| How many users can it take? | The 100-user failure was found, explained and fixed: 80 % failed uploads → 0 %, 0.33 → 56 ops/s (local re-measure) | 3 |
| What about large files? | Six types up to 500 MB byte-exact; 5,094 downloads, 0 integrity failures | 3 |
| Did testing find anything? | Two concurrency deadlocks, fixed, with a regression test and zero recurrences on staging | 4 |
| How would you know something broke? | Monitoring emails an alert; each of the three overloads on test night sent one | 5 |
| What if someone floods uploads? | Rate limits and email verification already; the quota gap was in the threat model and is now closed (PR #157) | 7 |
| Could the server redirect a share to itself? | Not silently: the recipient's key fingerprint is computed in the browser, confirmed, and pinned with a warning on change | 9 |
| Has anyone else checked it? | An OWASP ZAP scan of the live site: no High-risk issue; it caught missing headers on the static bundle, which we fixed. Dependency audits are clean ([scans](../security/scans-2026-10-04/README.md)) | REFLECTION 12 |
| Is it easy to use? | Real use by the supervisor, the Teaching Team and other students, and a walkthrough that changed four things; no formal study, so no score (NFR2) | 10 |
| Can you scan for viruses? | Not on the server under zero-knowledge; sharing scope, a download warning and endpoint antivirus instead | 8 |
| What if a deploy gets stuck? | The live site keeps running the previous release; a stalled dependency download is cut off and retried, and a failed build rolls back and is quarantined ([PR #196](https://github.com/jsonrar/fyp-secure-file-platform/pull/196)) | — |
