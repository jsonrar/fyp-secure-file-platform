# Non-expert usability study plan

[English](STUDY_PLAN.md) | [简体中文](STUDY_PLAN.zh-CN.md)

| | |
| --- | --- |
| **WBS package** | 5.4 Non-expert usability testing (`docs/PROPOSAL_TRACEABILITY.md`) |
| **Requirement** | NFR2 Understanding & Usability, High: *users can complete all operations without any specialized knowledge* |
| **Proposal verification** | "Functional testing with users lacking cryptography background" and a non-technical user demo review (RTM, Appendix A) |
| **Owner** | Testing & Deployment Lead |
| **Status** | **Not run.** Issue #115 was closed as not planned on 2026-10-04: the team chose informal real use (supervisor, team, Teaching Team, other students) over this study. No session has been run, so no result exists, and `RESULTS.md` is deliberately empty. The plan stays here in case a formal study is wanted later. |

This folder is the study kit: the plan (this file), the participant-facing materials in
[`materials/`](materials/), two CSV templates, and
[`backend/scripts/usability_analysis.py`](../../backend/scripts/usability_analysis.py), which
turns the recorded data into the verdict this plan commits to in advance. Nothing here
certifies the product as usable; it makes the claim testable.

## 1. Why this study, and what it can and cannot show

NFR2 is the only High-priority requirement whose verification step is *a human being*. The
Node and browser suites prove the buttons work; they cannot prove a person who has never heard
of RSA knows which button to press, or understands that a forgotten passphrase plus a lost key
file costs them their files. The proposal's own literature review (Reuter et al., 2021) names
key management as the adoption barrier this platform claims to remove, so this is the study
that tests the project's central claim.

**It can show** where non-experts get stuck, how often, and whether the product meets the
pre-registered thresholds in §6 on this sample.

**It cannot show** that the product is usable by the general public. With five to eight
participants the study finds most serious problems (Nielsen and Landauer's well-known result is
that five users surface roughly 85 % of them) but it is not statistically powered, the sample
is people the team can reach, and think-aloud slows people down, so the timings are
comparative, not benchmarks. State these limits wherever the results are quoted.

## 2. Settle these before the first session

These are decisions the team has to make; they are not in this plan's gift.

1. **Ethics and approval.** Running tasks with human participants may need approval or a
   documented exemption. This plan does **not** assume the answer: ask the supervisor
   (Dr. Asad Malik) in writing whether Monash requires ethics review for a usability evaluation
   of the team's own software, and file the reply under `02 Project Documents/`. If review is
   required, no session runs until it is granted. The consent sheet and screener assume the
   answer is "exempt, with informed consent".
2. ~~What the product tells a participant about losing everything.~~ **Settled 2026-10-01 by
   the project owner, and consistent with `docs/SECURITY_FLOWS.md`.** The registration copy is
   right: with the passphrase **or** the private key file the account can be reopened (the key
   file resets a forgotten passphrase in Settings), but with **neither**, nothing can recover
   the files, not the server and not a recovery officer; the only way forward is to delete the
   account and register again. *Request recovery* does not change that: it only asks an officer
   to rewrap one file's key to a registered key the requester can still use, so it does not
   rescue someone who has lost both. This is the answer key for Probe 2 in
   `materials/task-cards.md`. What stays open is a *usability* question the study should answer:
   whether a button called *Request recovery* on every file row leads people to believe that
   they are safe if they lose the key file.
3. **A second pair of hands.** One facilitator and one note-taker per session. A solo facilitator
   cannot both prompt neutrally and time accurately.
4. **A team-owned mailbox for verification codes.** Registration emails a code. Use plus-addressing
   on a team-owned mailbox (one address per participant) and put the inbox on a second screen
   for the participant to read from. Do not record that address in this repository, and do not
   ask participants to use their own email.
5. **A pilot.** Run one full session with a teammate who is *not* the facilitator, on the real
   staging site, and fix timings, wording and broken tasks before recruiting anyone else.

## 3. Participants

| | |
| --- | --- |
| **Target** | 6, minimum 5 (the analysis script refuses a verdict below 5) |
| **Include** | Adults who use a computer for study or work and who have shared a file online (email, a cloud drive, a chat app) |
| **Exclude** | Anyone who studies, works or has trained in IT, computer science or information security; anyone who has seen SecureView before; the team and their immediate collaborators |
| **Screening** | [`materials/screener.md`](materials/screener.md), three yes/no questions, no personal data kept for those screened out |
| **Pay** | None assumed. If a thank-you is offered, say so on the consent sheet |

Aim for a spread of age, first language and operating system rather than six similar students.
Record only what the analysis needs: a participant code (`P01`…), whether they used a Mac,
Windows or another system, and their browser. **No names, emails or photos are kept with the
data.** The sign-up sheet that links a name to a code is destroyed after the sessions.

## 4. Session protocol (about 55 minutes)

| Minutes | Step |
| --- | --- |
| 0–5 | Welcome, read the consent sheet aloud, answer questions, get a signature or a recorded verbal yes. Say plainly: **we are testing the product, not you**, and they may stop at any time. |
| 5–8 | Background questions (browser, how they usually share files). Do not explain the product. |
| 8–45 | Tasks T1–T10 from [`materials/task-cards.md`](materials/task-cards.md), one card at a time, think-aloud. |
| 45–50 | Post-test questionnaire: SEQ was collected per task; now the 10-item SUS and the open questions in [`materials/questionnaire.md`](materials/questionnaire.md). |
| 50–55 | Debrief, answer anything they asked to have explained, confirm their account was deleted (T10), thank them. |

**Setting.** The staging site, https://secureview.tech, on the participant's choice of the
team's laptop or their own, in a quiet room. The moderator sits beside, not behind. A second
screen shows the verification-code inbox (§2.4).

**Their data.** Each participant creates a throwaway account and a passphrase *they invent for
this session only*. Tell them not to use a password or passphrase they use anywhere else, and
that the facilitator will never ask them to say it aloud. Files are the harmless ones the team
puts on the desktop (`notes.txt`, a small image, a small PDF); never a participant's own file.
The last task deletes the account and its files, which is also the cleanup.

**Facilitator rules.** Read the scenario as written. Never use the product's own button or menu
names ("Upload", "Share", "Verified"): those are what the study measures. Answer questions with
"What would you do if I weren't here?". Intervene only on the hint ladder below, and record the
level.

| Hint level | What the facilitator may say | Outcome code |
| --- | --- | --- |
| 0 | Nothing | `success` |
| 1 | A neutral prompt: "What are you looking for?" or "What do you expect to happen?" | `assisted` |
| 2 | Name the area of the screen, not the control: "Take another look at the top of the page." | `assisted` |
| 3 | The facilitator does it, or the participant gives up, or the task budget runs out | `failed` |

A task also ends as `failed` when its time budget expires. Take the time from the first screen
of the scenario until the participant says they are done or reaches the success condition.

## 5. Measures

Per participant and task, recorded in [`observations-template.csv`](observations-template.csv):

- **Outcome** as above, and **time on task** in seconds;
- **Critical errors**, counted using the definition on each task card. A critical error is one
  that could cost the participant their files or expose them to someone they did not intend;
- **SEQ**, the Single Ease Question, asked straight after each task: "Overall, how difficult or
  easy was this task?", 1 (very difficult) to 7 (very easy);
- Free-form **notes**: where they hesitated, what they said, what they expected.

Per participant, in [`sus-template.csv`](sus-template.csv): the 10-item **System Usability
Scale** (Brooke, 1996), scored by the script (odd items x−1, even items 5−x, total × 2.5, range
0–100).

Plus two **comprehension probes** asked at the end of T1 and T9, answered in the participant's
own words and recorded verbatim in the notes. They test whether the person understands what
the passphrase and the key file are for, which task completion alone does not show.

## 6. Success criteria, fixed before any session

NFR2 is judged **met on this sample** only if every one of these holds. They are encoded in
`usability_analysis.py`; changing a threshold means changing this table first, in a commit
dated before the first session.

| # | Criterion | Why this number |
| --- | --- | --- |
| 1 | At least **5** participants complete the session | Fewer cannot support a verdict |
| 2 | **Every** task is completed unaided (`success`) by at least **80 %** of participants | NFR2 says *all operations*; a task most people fail is an operation they cannot do |
| 3 | No task has a **critical error** for more than **one** participant | A task that loses files for two people is not usable, whatever the average says |
| 4 | Mean **SUS ≥ 68** | 68 is the long-run average SUS across studies; below it the interface is rated worse than typical |
| 5 | Every participant has a SUS questionnaire | No silent drop-outs |

An assisted completion is *not* an unaided one: it counts toward `assisted`, not `success`.

If the criteria are **not** met, that is a valid result, and the deliverable is the findings
and the fixes, not a rewritten threshold. Do not report a verdict the data does not support.

## 7. Tasks

Ten tasks in a fixed order, because later ones depend on earlier ones (the account, the file,
the key file). Full scenario wording, success conditions, critical errors and time budgets are
in [`materials/task-cards.md`](materials/task-cards.md).

| ID | The participant is asked to… | Requirement |
| --- | --- | --- |
| T1 | Create an account and keep it recoverable (code from the email, passphrase, private key file) | FR1, FR4 |
| T2 | Sign out and sign back in | FR1 |
| T3 | Protect a file so only they can read it | FR2 |
| T4 | Find out whether the stored file has been altered | FR3 |
| T5 | Let a colleague read the file | FR5 |
| T6 | Stop the colleague from getting it | FR5 (revocation is a later extension of it) |
| T7 | Save a readable copy of a file a colleague shared with them | FR5, FR6 |
| T8 | Get back into their files, pretending the passphrase is forgotten | FR1, FR4 |
| T9 | Find out, in plain words, how their file is protected | FR9 |
| T10 | Delete their account | not in the proposal's RTM; also the session cleanup |

## 8. What to watch for (expert observations made before the study)

These come from reading the interface on 2026-10-01, not from users, so they are hypotheses
to look for, not findings. Each should be confirmed or dropped by the sessions.

- **Jargon on the upload page.** Beside the file picker a participant sees "File key
  wrapping: RSA-OAEP-SHA256", an algorithm dropdown and a "Recovery key fingerprint — verify
  this out of band before trusting an upload". NFR2 says no specialised knowledge. Watch T3 for
  hesitation, for people who stop to read it, and for people who touch the dropdown.
- **The upload page says "AES-256-GCM"** in its introduction while offering four algorithms.
  Watch whether anyone notices the contradiction.
- **Icon-only actions.** Each file row has small icon buttons whose names exist only as hover
  tooltips: *Download and decrypt*, *Download encrypted file*, *Access history*, *Share*,
  *Delete*, and *Request recovery* on every row (*Share* and *Delete* only on files the user
  owns). Each row also carries a "Folder" dropdown and a status button that doubles as the
  integrity check. Watch T4, T5 and T7 for the wrong download button, for hover-hunting, for
  anyone who never finds *Share*, and for people who do not realise the status button is
  clickable.
- **Two secrets that look alike.** Registration asks for a password and a different
  "encryption passphrase". Watch T1/T2/T5 for entering the wrong one, and the comprehension
  probe for whether they can say which is which.
- **The `.pem` key file.** The page says the computer may have no application for it. Watch
  T1 for people who tick "I have saved this" without downloading, and T8 for whether they can
  find the file again.

## 9. Analysis and reporting

1. Copy `observations-template.csv` and `sus-template.csv` to a working location (not into a
   commit until the participant codes are anonymous), fill one row per task and per person.
2. Run `python backend/scripts/usability_analysis.py observations.csv sus.csv` for the tables
   and the verdict, or add `--check` to get a non-zero exit when NFR2 is not met.
3. Rate each distinct problem in [`issue-log-template.csv`](issue-log-template.csv) with
   Nielsen's severity scale: **0** not a problem, **1** cosmetic, **2** minor, **3** major,
   **4** catastrophic. A critical error is at least a 3.
4. Fill in [`RESULTS.md`](RESULTS.md): the table, the verdict, the top findings with severity
   and the number of participants affected, the limits in §1, and the participant quotes that
   explain the numbers. Do not publish identifying detail.
5. Open one GitHub Issue per severity 3–4 finding (label `area:frontend`, plus `usability`),
   fix, and re-run the affected tasks with new participants where the change is large.
6. Update `docs/PROPOSAL_TRACEABILITY.md` (WBS 5.4 → Done only when `RESULTS.md` exists and
   the verdict is recorded, whichever way it falls), the changelog, and both TODO summaries in
   the same pull request.

## 10. Schedule and roles

| When | What | Who |
| --- | --- | --- |
| Before anything | §2 decisions; written ethics answer | Testing Lead, Backend Lead (accounts), Crypto Lead (§2.2) |
| Week 0 | Pilot with a teammate; fix the kit | Testing Lead |
| Week 1 | Recruit and screen; book sessions | Testing Lead |
| Weeks 1–2 | Sessions (about 55 min each, at most three a day) | Facilitator + note-taker |
| Week 2 | Analysis, severity rating, `RESULTS.md` | Testing Lead |
| Week 3 | Fix severity 3–4 findings; re-test the affected tasks | Frontend Lead |

Dates are not fixed here: they depend on §2.1 and on the final-demo date, which the team
should confirm with the supervisor.

## 11. Data protection

- A participant code, platform and browser are the only data kept. No names, no email
  addresses, no photographs. No audio or screen recording unless the consent sheet offers it
  and the participant agrees; if it is used, it is deleted when `RESULTS.md` is finished.
- Participants never type a real password or a passphrase they use elsewhere, and the
  facilitator never asks for it. Accounts and files are deleted in T10, and the facilitator
  confirms in the admin or by trying to sign in.
- Raw CSVs with only participant codes may be committed once the sign-up sheet is destroyed;
  until then they stay out of the repository.

## 12. Limitations to repeat in every report

- A small convenience sample, not a statistically powered one.
- Staging environment and a moderator in the room; real-world use has neither.
- Think-aloud slows people down, so times compare tasks and revisions, not absolute speed.
- One browser on one operating system per person; Android, Firefox and low-end hardware are
  not covered, matching the gaps recorded in `docs/THREAT_MODEL.md` §9.
- The study tests understanding of the product's own messages, not whether anyone will
  actually keep a key file safe weeks later.
