/**
 * Record the Help page's walkthrough videos from the real product.
 *
 *   node scripts/record-walkthroughs.mjs --base http://localhost:5174 \
 *     --accounts /path/to/video-accounts.json --out public/videos
 *
 * It drives a real, running stack (frontend + API + MySQL) in Chromium, the way a person would:
 * it types visibly, outlines each control before clicking it, and shows a caption bar saying
 * what is happening and why. Nothing is mocked: the upload is really encrypted in the browser,
 * really shared by re-wrapping the key, and really decrypted by the recipient.
 *
 * `--accounts` is a JSON file `{ "sam": {username, password, passphrase}, "alex": {...} }` for
 * two existing accounts on that stack (create them with backend/scripts/seed_test_account.py,
 * using made-up names and @example.com addresses). Point it only at a disposable local stack: the
 * credentials are typed on screen and end up in the video's keystrokes (passphrases are masked
 * by the page, but use throwaway values anyway).
 *
 * Output, in `--out`: encrypt-upload.mp4, share-open.mp4 and how-it-works.mp4 (the animated
 * explainer in present mode), each with a .jpg poster. Needs ffmpeg on PATH.
 */

import { execFileSync } from 'node:child_process'
import { mkdirSync, mkdtempSync, readFileSync, renameSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join, resolve } from 'node:path'

import { chromium } from '@playwright/test'

const args = Object.fromEntries(
  process.argv.slice(2).reduce((pairs, value, i, all) => (value.startsWith('--') ? [...pairs, [value.slice(2), all[i + 1]]] : pairs), []),
)
const BASE = args.base ?? 'http://localhost:5174'
const OUT = resolve(args.out ?? 'public/videos')
const ONLY = args.only ? args.only.split(',') : null
const accounts = JSON.parse(readFileSync(args.accounts, 'utf8'))
const SIZE = { width: 1280, height: 720 }
const FILE_NAME = 'Project notes.txt'
const FILE_TEXT =
  'Project notes\n\nMilestone 3 is due on Friday. Budget review moved to Monday.\n' +
  'These notes are encrypted in the browser before upload; the server stores only ciphertext.\n'

mkdirSync(OUT, { recursive: true })
const work = mkdtempSync(join(tmpdir(), 'sv-video-'))

/** Injected into every page: a caption bar and an outline for the control about to be used. */
const OVERLAY = `
(() => {
  const css = \`
    #sv-cap { position: fixed; left: 50%; bottom: 22px; transform: translateX(-50%); z-index: 2147483647;
      max-width: 1040px; width: calc(100% - 48px); display: flex; gap: 14px; align-items: center;
      padding: 14px 20px; border-radius: 16px; background: rgba(15, 23, 42, 0.92); color: #fff;
      font: 500 17px/1.45 system-ui, -apple-system, Segoe UI, sans-serif; box-shadow: 0 10px 30px rgba(0,0,0,.25);
      transition: opacity .3s; }
    #sv-cap[hidden] { display: none; }
    #sv-cap b { flex: none; display: inline-flex; align-items: center; justify-content: center;
      min-width: 34px; height: 34px; border-radius: 999px; background: rgb(0, 109, 199); font-size: 15px; }
    #sv-cap small { display: block; font-weight: 400; color: #cbd5e1; font-size: 14px; margin-top: 2px; }
    .sv-focus { outline: 3px solid rgb(0, 109, 199) !important; outline-offset: 4px !important;
      border-radius: 8px; box-shadow: 0 0 0 9px rgba(0, 109, 199, .18) !important; transition: outline-color .2s; }
  \`;
  const install = () => {
    if (document.getElementById('sv-cap')) return;
    const style = document.createElement('style'); style.textContent = css; document.head.appendChild(style);
    const cap = document.createElement('div'); cap.id = 'sv-cap'; cap.hidden = true; document.body.appendChild(cap);
    const saved = sessionStorage.getItem('sv-cap');
    if (saved) window.__svCaption(...JSON.parse(saved));
  };
  window.__svCaption = (step, text, sub) => {
    sessionStorage.setItem('sv-cap', JSON.stringify([step, text, sub]));
    const cap = document.getElementById('sv-cap'); if (!cap) return;
    cap.hidden = !text;
    cap.innerHTML = (step ? '<b>' + step + '</b>' : '') + '<div>' + (text || '') + (sub ? '<small>' + sub + '</small>' : '') + '</div>';
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', install); else install();
})();
`

const pause = (page, ms) => page.waitForTimeout(ms)

/** Show a caption and hold it long enough to be read: about 45 ms a character, 1.8–5 s. */
async function caption(page, step, text, sub = '') {
  await page.evaluate(([s, t, u]) => window.__svCaption?.(s, t, u), [step, text, sub])
  await page.waitForTimeout(Math.min(5000, Math.max(1800, (text.length + sub.length) * 45)))
}

/** Outline a control, give the viewer a moment to see it, then act on it. */
async function point(locator, ms = 900) {
  // Centre it, so the caption bar along the bottom never covers what it is talking about.
  await locator.evaluate((el) => {
    el.scrollIntoView({ block: 'center', behavior: 'smooth' })
    el.classList.add('sv-focus')
  })
  await locator.page().waitForTimeout(ms)
}
async function unpoint(locator) {
  // The control is often gone by now (a click that navigates), so do not wait for it.
  await locator.evaluate((el) => el.classList.remove('sv-focus'), null, { timeout: 500 }).catch(() => {})
}
async function click(locator, ms) {
  await point(locator, ms)
  await locator.click()
  await unpoint(locator)
}
async function type(locator, text, { secret = false } = {}) {
  await point(locator, 500)
  await locator.click()
  await locator.pressSequentially(text, { delay: secret ? 25 : 55 })
  await unpoint(locator)
}

async function signIn(page, account, step) {
  await page.goto(`${BASE}/login`)
  await caption(page, step, `Sign in as ${account.username} with the account password`, 'The password only signs you in. It does not open your files.')
  await type(page.getByRole('textbox', { name: 'Username' }), account.username)
  await type(page.getByRole('textbox', { name: /^Password/ }), account.password, { secret: true })
  await click(page.getByRole('button', { name: 'Login' }), 500)
  await page.getByRole('heading', { name: 'Your Workspace' }).waitFor()
  await pause(page, 900)
}

async function signOut(page) {
  await page.getByRole('button', { name: /^Account menu for/ }).hover()
  await pause(page, 500)
  await page.getByRole('menuitem', { name: 'Log out' }).click()
  await page.getByRole('heading', { name: 'Sign In' }).waitFor()
}

async function unlockIfAsked(page, account, step) {
  const heading = page.getByRole('heading', { name: 'Unlock your files' })
  if (!(await heading.isVisible().catch(() => false))) {
    await heading.waitFor({ timeout: 4000 }).catch(() => {})
  }
  if (!(await heading.isVisible().catch(() => false))) return
  await caption(page, step, 'Unlock your key with the encryption passphrase', 'It opens your private key here in the browser. It is never sent to the server.')
  await type(page.getByRole('textbox', { name: /^Encryption passphrase/ }), account.passphrase, { secret: true })
  await click(page.getByRole('button', { name: 'Unlock', exact: true }), 500)
}

async function recordFlow(name, flow) {
  if (ONLY && !ONLY.includes(name)) return
  const browser = await chromium.launch()
  const context = await browser.newContext({
    viewport: SIZE,
    colorScheme: 'light',
    acceptDownloads: true,
    recordVideo: { dir: work, size: SIZE },
  })
  await context.addInitScript(OVERLAY)
  const page = await context.newPage()
  page.setDefaultTimeout(60_000)
  try {
    await flow(page)
  } finally {
    const video = page.video()
    await context.close()
    await browser.close()
    const raw = await video.path()
    const webm = join(work, `${name}.webm`)
    renameSync(raw, webm)
    encode(webm, name)
  }
}

/** H.264 MP4 that plays everywhere, with the first blank half-second trimmed, plus a poster. */
function encode(webm, name) {
  const mp4 = join(OUT, `${name}.mp4`)
  execFileSync('ffmpeg', ['-loglevel', 'error', '-y', '-ss', '0.6', '-i', webm, '-an', '-c:v', 'libx264',
    '-preset', 'slow', '-crf', '30', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', mp4])
  execFileSync('ffmpeg', ['-loglevel', 'error', '-y', '-ss', '4', '-i', mp4, '-frames:v', '1',
    '-q:v', '4', join(OUT, `${name}.jpg`)])
  console.log(`wrote ${mp4}`)
}

// --- 1. Encrypt and upload -----------------------------------------------------------------
await recordFlow('encrypt-upload', async (page) => {
  const sam = accounts.sam
  const file = join(work, FILE_NAME)
  writeFileSync(file, FILE_TEXT)

  await signIn(page, sam, 1)
  await caption(page, 2, 'Open Upload')
  await click(page.getByRole('navigation').getByRole('link', { name: 'Upload', exact: true }))
  await page.getByRole('heading', { name: 'Encrypt Your Files' }).waitFor()

  await caption(page, 3, 'Choose the file to protect', 'Drag it in or use Select Files. Several files at once are fine.')
  const picker = page.locator('label').filter({ hasText: 'Select Files' })
  await point(picker, 1100)
  await page.getByLabel('Select Files').setInputFiles(file)
  await unpoint(picker)
  await pause(page, 1200)

  await caption(page, 4, 'Pick the cipher — AES-256-GCM is the default', 'AES-GCM-SIV, ChaCha20, XChaCha20 and AES-128/192 are here too. All of them detect tampering.')
  await point(page.getByRole('combobox').first(), 2200)
  await unpoint(page.getByRole('combobox').first())

  await caption(page, 5, 'Start Encryption', 'Your browser encrypts the file with a new random key. Only the scrambled result is uploaded.')
  await click(page.getByRole('button', { name: 'Start Encryption' }), 1000)
  await page.getByRole('button', { name: 'Encryption Complete' }).waitFor({ timeout: 60_000 })
  await pause(page, 1500)

  await caption(page, 6, 'Your file is now stored encrypted')
  await click(page.getByRole('button', { name: 'View Encrypted Files' }))
  const row = page.getByRole('row').filter({ hasText: FILE_NAME }).first()
  await row.waitFor()
  await caption(page, 6, 'Same size before and after — that is expected', 'The authentication tag and nonce are stored separately, so the ciphertext is exactly as long as the file.')
  await point(row, 2600)
  await unpoint(row)

  await caption(page, 7, 'Encrypted preview: what the server actually holds', 'Random-looking bytes. A text file would start with readable letters; this does not.')
  await click(row.getByRole('button', { name: 'Encrypted preview' }))
  const preview = page.getByTestId('ciphertext-preview').first()
  await point(preview, 4500)
  await unpoint(preview)
  await caption(page, '✓', 'Done. Next: share it with someone, in the second video.')
  await pause(page, 2500)
})

// --- 2. Share, and the recipient opens it ----------------------------------------------------
await recordFlow('share-open', async (page) => {
  const sam = accounts.sam
  const alex = accounts.alex

  await signIn(page, sam, 1)
  await caption(page, 2, 'In My Files, press Share on the file')
  await click(page.getByRole('navigation').getByRole('link', { name: 'My Files', exact: true }))
  const row = page.getByRole('row').filter({ hasText: FILE_NAME }).first()
  await row.waitFor()
  await click(row.getByRole('button', { name: 'Share', exact: true }))
  // Sharing needs Sam's key, so the first share of a session asks for the passphrase.
  await unlockIfAsked(page, sam, 3)
  await page.getByRole('heading', { name: 'Share this file' }).waitFor()

  const recipientField = page.getByRole('textbox', { name: /their username/i })
  await caption(page, 4, `Enter the other person’s username: ${alex.username}`, 'They need a SecureView account. There is no public link that could leak.')
  await type(recipientField, alex.username)
  const dialog = page.locator('form').filter({ has: recipientField })
  await caption(page, 5, 'Share', 'Your browser re-seals the file key for Alex’s public key. The file itself is not copied.')
  await click(dialog.getByRole('button', { name: 'Share', exact: true }), 900)
  await page.getByText(`Shared with ${alex.username}`).first().waitFor({ timeout: 60_000 })
  await caption(page, 6, `Shared with ${alex.username}`, 'You can revoke this at any time from the same dialog.')
  await pause(page, 2600)
  await page.getByRole('button', { name: 'Cancel' }).click().catch(() => {})
  await signOut(page)

  await signIn(page, alex, 7)
  await caption(page, 8, 'Alex finds it under Shared with me')
  await click(page.getByRole('navigation').getByRole('link', { name: 'My Files', exact: true }))
  await click(page.getByRole('button', { name: /^Shared with me/ }))
  const shared = page.getByRole('row').filter({ hasText: FILE_NAME }).first()
  await shared.waitFor()
  await point(shared, 1600)
  await unpoint(shared)

  await caption(page, 9, 'Download and decrypt', 'Alex uses Alex’s own passphrase. Nobody had to send anyone a password.')
  await click(shared.getByRole('button', { name: 'Download and decrypt' }))
  await unlockIfAsked(page, alex, 10)
  await page.getByText(`Decrypted and saved ${FILE_NAME}`).first().waitFor({ timeout: 60_000 })
  await caption(page, '✓', 'Decrypted and checked', 'The authentication tag and SHA-256 matched, so this is exactly the file Sam uploaded.')
  await pause(page, 3500)
})

// --- 3. The animated explainer, in present mode --------------------------------------------------
await recordFlow('how-it-works', async (page) => {
  await page.goto(`${BASE}/how-it-works?present`)
  await page.getByTestId('story-present').waitFor()
  // Seven scenes at eight seconds each, and a moment on the last one.
  await pause(page, 7 * 8000 + 2500)
})

rmSync(work, { recursive: true, force: true })
