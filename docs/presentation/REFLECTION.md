# Reflection: what is still missing, and how to fix it (kept up to date)

[English](REFLECTION.md) | [简体中文](REFLECTION.zh-CN.md)

The shortcomings we found ourselves: the problem, the fix, its priority and where it stands. When an
item is done, change its status to Done with the PR number. Anything not finished stays as it is; never
mark it done early. What to say and where the evidence is: [TALKING_POINTS.md](TALKING_POINTS.md).

Last updated: 2026-10-04

## How these were found

- **A first-time-user walkthrough (2026-10-04):** registering a brand-new account on a local stack and
  going through register → save private key → sign in → upload → unlock → share, noting every point
  where a newcomer would hesitate or get stuck.
- **The capacity test (#140):** it measured the first performance bottleneck.
- **The threat model (`docs/THREAT_MODEL.md`):** findings already recorded as open.
- **The Final Presentation guidance (Ed #66):** what the nine parts of a 12-minute talk need that we
  do not have yet.

## 1. Usability

| # | Problem | Fix | Priority | Status |
| --- | --- | --- | --- | --- |
| 2 | Each file row has six unlabelled icons. Share, a core feature, is just an icon; Share, Delete and Access history have no accessible name; at ~800 px the Help assistant button covers the Delete icon. | Show Download (decrypt), Share and Delete with labels; put Download encrypted, Request recovery and Access history under "More"; give every button an accessible name; fix the overlap. | Must | **Done** (PR #159). The homepage picture guide still shows the old icons and is re-captured with the demo material (item 1). |
| 8 | Sharing has no confirmation: it happens the moment a username is entered, so a typo shares with a stranger. | Before sharing, show "Sharing with X (key fingerprint ab12…)" and ask to confirm. The fingerprint can be checked in person, which also guards against the server substituting the recipient's public key (a man-in-the-middle). | Strongly recommended | **Done** (PR #160): confirmation step, fingerprint computed in the browser, the user's own fingerprint in Settings, a warning when a recipient's key changes. Threat model T-S5 mitigated. |
| 10 | Registration is one form with six required fields and three secrets to understand (login password, encryption passphrase, private-key file), then a second sign-in. | Split into two steps (account, then encryption), explain in one sentence why there are two passwords, and sign the user in straight after. | Optional (the demo uses prepared accounts) | **Done** (PR #161): step 1 account, step 2 the passphrase with a "why a second password" note; registering signs the user in and opens the session key with the key just generated. |
| 11 | A first sign-in has no guidance; a newcomer does not know the flow is upload → share → recipient downloads and verifies. | A three-step checklist on the dashboard that ticks itself as each step is done; the live demo follows it too. | Optional | **Done** (PR #162): three steps on the dashboard that tick themselves from the account's own audit trail, each linking to where it is done; hideable per account. |
| — | Uploads finished "instantly" and looked unencrypted. | Show the real encryption steps, measured times and the bytes before and after. | Must | **Done** (PR #156) |
| — | After the "Sealed" restyle the pages still disagreed with each other: headings left-aligned on some pages and centred on others, widths from a narrow strip to full width, the sidebar vanishing on Help and Education, 12 px body text. We found it by looking page by page, which is why it took several rounds. | A shared `PageHeader` and one content container, two-column Settings and Profile, the sidebar on every signed-in page, and a committed audit script (`frontend/scripts/layout-audit.mjs`) that measures all pages in five configurations, so this is checked by a script and not by eye. | Strongly recommended | **Done** for headers, widths, sidebar and text size ([#183](https://github.com/jsonrar/fyp-secure-file-platform/issues/183)); dark-mode primary, heading pills and the sign-in layout are #184 (done); the rest is #185. Remaining weakness: the audit measures layout, not whether a page is good, and pages still have no component tests. |

## 2. Performance and reliability

| # | Problem | Fix | Priority | Status |
| --- | --- | --- | --- | --- |
| 6 | At 100 concurrent users the API's 15 database connections run out and 65–78 % of uploads get HTTP 500 while CPU is at 3 %. The guess is that a file transfer holds its connection throughout; this has not been verified in the code. | Verify where the connection is held; release it before the transfer if possible, then enlarge the pool or add workers as needed; re-run 100 users on staging with the same tool for a before/after chart. The re-run needs an evening. | Strongly recommended | **Done locally** (PR #163): the cause was uploads holding a connection while awaiting a thread pool whose threads were waiting for connections, not file transfers (measured). 100 users locally: 80 % failed → 0 %, 0.33 → 56 ops/s. Staging re-run still to do. |
| — | Load-test transfer speeds are bounded by the home link (~24 Mbit/s up), so the server's own port (~100 Mbit/s) was never the limit. | State it in the report; use a better-connected generator if one is available. | State it | Stated in the report |
| — | `db_retry` does not log a retry, so we can show no deadlock reached a user but not whether a retry fired. | Log a warning on each retry. | Optional | To do (with #6) |
| — | In-browser encryption peaks at about 4× the file size in memory, so 500 MB files likely fail on phones (threat model F-19). | A large-file warning exists; a real fix is chunked streaming encryption, beyond this semester. | State it | Recorded in the threat model |
| — | A docs-only push could cancel the CI run of the code merged just before it and then skip the tests itself, so that code was never promoted to `deploy` (seen on 2026-10-04: #168 cancelled #169's run). | Judge a push to `main` against `deploy`, not against the previous push. | Must | Done: [#171](https://github.com/jsonrar/fyp-secure-file-platform/pull/171) |
| — | On the self-hosted runners' first runs the `backend` job took about 33 minutes against 3–6 for every other job. Its uv cache had never been saved, because the first run failed before the save step. | Check whether the CPU cap is the cause before raising it, since the cap protects production on the same VPS. | Should | Done, no change needed: with the cache saved, `backend` took 1 min 34 s and the whole run about 8 minutes (#171). It was the cold cache. |

## 3. Security

| # | Problem | Fix | Priority | Status |
| --- | --- | --- | --- | --- |
| — | No per-account storage quota: one account could fill a disk shared with other services (threat model T-D2 / F-09). | Per-account quota, a 24-hour upload volume, a free-disk floor, per-IP concurrent uploads in nginx, an `UPLOAD_BURST` rule. | Must | **Done** (PR #157) |
| — | The server cannot scan for viruses (inherent in zero-knowledge encryption). | Warn before downloading a shared program or macro file; rely on endpoint antivirus; never send hashes to a third party. | Must | **Done** (PR #157) |
| 12 | No third-party security scan; "secure" is only our own word. | An OWASP ZAP baseline scan of staging plus `pip-audit` / `npm audit`; fix what they find and commit the report. | Optional | Done: [scans-2026-10-04](../security/scans-2026-10-04/README.md). ZAP: 0 FAIL, 8 WARN, no High. It found a real gap: the JS/CSS bundle was served without HSTS or nosniff, because an nginx location that adds its own header silently drops the server-level ones; fixed, with a test. Six advisories in a test-only HTTP client fixed by upgrading. The nginx change still has to be installed on the VPS. |
| — | The server sees metadata (file name, size, type, times). | A design trade-off; say so in the talk. Encrypted file names are future work. | State it | Recorded in the threat model |
| — | No multi-factor sign-in. | Future work. | State it | — |
| — | Volumetric DDoS cannot be stopped in the application. | A real deployment sits behind a service such as Cloudflare; present it as a known risk outside scope. | State it | — |

## 4. Presentation and evidence

| # | Problem | Fix | Priority | Status |
| --- | --- | --- | --- | --- |
| 3 | "We encrypt" has no moment the audience can see for themselves. | A tamper demonstration: change one byte of stored ciphertext and the recipient's download fails at once. The CI tamper drill already does this; it needs a demo script. | Must | Done: `backend/scripts/demo_tamper.py` and [TAMPER_DEMO.md](TAMPER_DEMO.md). Rehearsing it showed two things: a refused download only said "Download failed", because the error body arrived as bytes and was never read (fixed, the row now turns Modified); and rewriting the database digest as well is still caught by the audit-chain anchor, a second layer worth showing. |
| 1 | Only about 4 of the 12 minutes are demo, and a live demo can lose the network, hang or be mis-clicked. | A 4-minute demo script; **demo accounts on staging must be created by the user** (the assistant does not register accounts on the live site); a recorded backup video. | Must | Script done: [DEMO_SCRIPT.md](DEMO_SCRIPT.md) (timed steps, lines to say, checklists, fallbacks). The demo accounts exist on staging, the backup video is recorded ([media/demo-backup.mp4](media/demo-backup.mp4)) and the picture guide was re-captured (PR #166). Still with the user: pre-share `quarterly-results.txt` from `demo-alice` to `demo-bob` on staging. |
| 4 | The slides have no diagrams yet. | Architecture diagram, encryption flow, requirements status table, limitations slide. Screenshots and numbers must come from the final version, so this is last. | Must | To do (9th) |
| 5 | NFR2 (usability) has no formal result: the study was not run (#115, closed as not planned). | Say it is supported by informal real use, never that a study verified it. | Must | Done: the wording to use, and what not to say, is in TALKING_POINTS §10. |
| 7 | No real-user data. | 5–8 students who have never used it, scored with SUS. | Strongly recommended | Not doing: #115 closed as not planned on 2026-10-04. The supervisor, the team, the Teaching Team and other students have used staging instead; that is informal use, with no SUS score. The study kit was deleted on 2026-10-05. |

## Order (decided 2026-10-04)

**2 → 8 → 10 → 11 → 6 → 3 → 12 → 1 → 4 → 5**

- 2, 8, 10 and 11 first: they are the usability problems. (The usability study, item 7, was later dropped; see its row.)
- 6 needs an evening on staging for the re-run, so it follows the code changes.
- 3 and 12 produce evidence and do not depend on the final UI.
- 1, 4 and 5 last, because the demo script, screenshots and numbers must come from the final version.

## Explicitly out of scope this semester

- Chunked streaming encryption (the large-file-on-phone problem)
- Encrypting file names and other metadata
- Multi-factor sign-in
- Network-level DDoS protection
- Files above 1 GB, collaborative editing, encrypted full-text search (see "Explicitly deferred" in `TODO.md`)
