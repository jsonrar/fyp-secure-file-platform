# Task cards / 任务卡

Facilitator copy. Read the **Scenario** aloud exactly as written (English or 中文, the
participant's choice) and show the participant only the scenario, never this page. Do **not**
use the product's own button or menu names. Start the clock when you finish reading; stop it at
the success condition, when they say they are done, or when the budget runs out (outcome
`failed`). After each task ask the SEQ: *"Overall, how difficult or easy was that? 1 is very
difficult, 7 is very easy."* Record everything in `observations-template.csv`.

主持人用。请逐字朗读**情景**（英文或中文，由参与者选择），只给参与者看情景，不要给他们看本页。**不要**
使用产品自己的按钮或菜单名称。读完开始计时；达到成功条件、参与者说做完了、或用完时限（记为 `failed`）
时停止。每个任务之后询问 SEQ：“总体来说，这个任务有多难或多容易？1 是非常困难，7 是非常容易。”
所有记录写入 `observations-template.csv`。

Setup before each session / 每场开始前: a throwaway mailbox address for the participant on the
second screen; a second account `buddy-Pnn` (already registered, passphrase known to the team,
having uploaded one small file `from-buddy.txt` and shared it with the participant's username
**after** T6 is done, see T7 note); three harmless files on the desktop (`notes.txt`, a small
image, a small PDF). Use a fresh browser profile. The account name of the participant is
`Pnn` plus a random suffix they choose.

---

## T1 — Create an account and keep it recoverable / 创建账户并确保可恢复

**Scenario (EN).** A colleague told you to use a service called SecureView to keep your private
documents safe. Open https://secureview.tech and set up your own account. The email with your
verification code will appear on the second screen.

**情景（中）。** 同事让你用一个叫 SecureView 的服务来保护私人文件。请打开 https://secureview.tech，为自己
创建一个账户。验证码邮件会出现在第二块屏幕上。

- **Success:** the account exists, the private key file has been downloaded, and they proceed
  to sign-in after reading the key page.
- **Critical errors (count each):** (a) ticks "I have saved this private key" without ever
  downloading it; (b) closes or leaves the key page without downloading it.
- **Budget:** 8 minutes. Allow the code email up to 2 minutes without counting it as hesitation.
- **Probe 1 (ask right after the task, record verbatim):** *"In your own words, what is the
  encryption passphrase for? And what is the file you just downloaded for?"*
  Answer key: the passphrase unlocks the account's key in the browser so files can be read;
  the key file is a backup that gets them back in if the passphrase is forgotten. Score each
  half 0/1 in the notes.

## T2 — Sign out and sign back in / 退出并重新登录

**Scenario (EN).** You are finished for now. Leave the site safely, then come back and get into
your account again.

**情景（中）。** 你暂时用完了。请安全地离开这个网站，然后再回来重新进入你的账户。

- **Success:** signed in again at the files area.
- **Critical errors:** none defined.
- **Budget:** 3 minutes.
- **Note:** watch for confusion between the login **password** and the encryption
  **passphrase**; record which one they try first.

## T3 — Protect a file / 保护一个文件

**Scenario (EN).** You have a document on the desktop called `notes.txt`. Make it so that only
you can read it, and so that it is stored safely online.

**情景（中）。** 桌面上有一个叫 `notes.txt` 的文档。请让它只有你自己能读，并安全地存放在网上。

- **Success:** the file appears in their file list as stored.
- **Critical errors:** none defined.
- **Budget:** 5 minutes.
- **Note:** record whether they read, ask about, or change the algorithm dropdown, and whether
  they say anything about "key wrapping" or the recovery key fingerprint (plan §8).

## T4 — Check the file has not been altered / 确认文件没有被改动

**Scenario (EN).** You worry someone could have tampered with the stored copy of `notes.txt`.
Find out whether it is still exactly what you stored.

**情景（中）。** 你担心有人可能改动了 `notes.txt` 的存储副本。请弄清它是否仍然和你存进去的完全一致。

- **Success:** they find and read the integrity status for that file and state the result.
- **Critical errors:** none defined.
- **Budget:** 4 minutes.

## T5 — Let a colleague read the file / 让同事能读这个文件

**Scenario (EN).** Your colleague has a SecureView account with the username `buddy-Pnn`. Let
them read `notes.txt`.

**情景（中）。** 你的同事有一个 SecureView 账户，用户名是 `buddy-Pnn`。请让他能读 `notes.txt`。

- **Success:** `buddy-Pnn` appears in the list of people the file is shared with.
- **Critical errors:** shares with a different user (the file reaches someone they did not
  intend). Being unable to unlock and giving up is `failed`, not a critical error.
- **Budget:** 6 minutes.
- **Note:** an unlock prompt will appear. Record whether they understand why they are asked
  for the passphrase again.

## T6 — Stop the colleague from getting it / 不再让同事拿到它

**Scenario (EN).** You have changed your mind. Make sure your colleague can no longer get
`notes.txt`.

**情景（中）。** 你改变主意了。请确保同事不能再拿到 `notes.txt`。

- **Success:** `buddy-Pnn` no longer appears in the shared list, after they confirm the prompt.
- **Critical errors:** deletes the file itself instead of removing the colleague's access
  (this loses the participant's own copy).
- **Budget:** 4 minutes.

## T7 — Save a readable copy of a file shared with you / 保存别人分享给你的文件

**Setup:** now, after T6, the facilitator signs in as `buddy-Pnn` on another device and shares
`from-buddy.txt` with the participant, then says: *"Your colleague has just shared another
file with you."*

**Scenario (EN).** Your colleague says they sent you a file called `from-buddy.txt`. Save a
copy of it onto your computer so you can open and read it.

**情景（中）。** 同事说他发给你一个叫 `from-buddy.txt` 的文件。请把它保存到你的电脑上，让你能打开并
读懂它。

- **Success:** the participant has a readable `from-buddy.txt` on the computer and can open it.
- **Critical errors:** none defined, but record if they save the *encrypted* copy and believe
  it is the readable one (the file row offers both).
- **Budget:** 5 minutes.

## T8 — Get back in after forgetting the passphrase / 忘记 passphrase 后重新进入

**Scenario (EN).** Pretend that you have forgotten your encryption passphrase. You still want
to open `notes.txt`. Get back into your files.

**情景（中）。** 假设你忘记了加密 passphrase，但你仍然想打开 `notes.txt`。请想办法重新进入你的文件。

- **Success:** they unlock using the key file from T1.
- **Critical errors:** (a) uploads or pastes the key file somewhere other than the product's
  own unlock dialog; (b) cannot find the key file and does not try to recover it (record, then
  the facilitator ends the task as `failed`).
- **Budget:** 6 minutes.
- **Optional continuation (not scored):** ask whether they would now set a new passphrase, and
  where they think that is done.

## T9 — Understand how the file is protected / 了解文件是如何被保护的

**Scenario (EN).** A friend asks you how SecureView actually keeps a file safe. Find something
on the site that helps you answer, in plain words.

**情景（中）。** 一位朋友问你，SecureView 到底是怎么保护文件的。请在网站上找一找能帮你回答的内容，并用
通俗的话说出来。

- **Success:** they reach the Education area and explain, in their own words, one thing about
  how the file is protected, without reading the page's words back verbatim.
- **Critical errors:** none defined.
- **Budget:** 5 minutes.
- **Probe 2 (record verbatim):** *"If you lost both your passphrase and your key file, what
  would happen to your files?"* **Answer key: to be fixed by the team before the first session
  (plan §2.2).** Until then, do not score this probe as right or wrong; record the words.

## T10 — Delete the account / 删除账户

**Scenario (EN).** You have finished trying SecureView and do not want it to keep anything
about you. Remove your account and everything stored in it.

**情景（中）。** 你试用完了 SecureView，不希望它保留任何关于你的信息。请删除你的账户以及其中存放的一切。

- **Success:** the account is deleted and signing in with it no longer works.
- **Critical errors:** none defined.
- **Budget:** 4 minutes.
- **This is also the cleanup.** Confirm by trying to sign in. Delete `buddy-Pnn` and the
  mailbox alias afterwards.
