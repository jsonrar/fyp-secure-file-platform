/**
 * The golden path in a real browser: register, verify, sign in, unlock, upload, download,
 * share, revoke, sign out -- by clicking the built pages, against the disposable stack.
 *
 * The Node live suites (`src/e2e`, `src/crypto/*.integration.test.ts`) already prove the
 * crypto and the API contract. What only a browser can prove is that the buttons are wired
 * to that logic: a Share button whose handler does nothing passes every Node suite and
 * fails here.
 *
 * Every identity, password, passphrase and file byte is minted per run and obviously fake:
 * `@example.com` addresses, "Throwaway" passwords, a generated file. The accounts live in
 * a database that is destroyed with the stack.
 */
import { randomBytes, randomUUID } from 'node:crypto'
import { readFile } from 'node:fs/promises'

import { expect, test, type Browser, type Page } from '@playwright/test'

import { takeVerificationCode } from './mailbox'

interface Account {
  username: string
  email: string
  password: string
  passphrase: string
}

function newAccount(role: string): Account {
  const run = randomUUID().slice(0, 8)
  return {
    username: `pw-${role}-${run}`,
    email: `pw-${role}-${run}@example.com`,
    password: `Throwaway!${randomUUID()}`,
    passphrase: `throwaway ${role} passphrase ${randomUUID()}`,
  }
}

const alice = newAccount('alice')
const bob = newAccount('bob')

// Every byte value, then random bytes: a text-only path cannot pass, and there is no
// meaningful content to leak. The test compares bytes and never prints them.
const fileName = `pw-smoke-${randomUUID().slice(0, 8)}.bin`
const fileBytes = Buffer.concat([
  Buffer.from(Array.from({ length: 256 }, (_, i) => i)),
  randomBytes(4096),
])

const pages: Page[] = []

async function openPage(browser: Browser): Promise<Page> {
  const context = await browser.newContext()
  const page = await context.newPage()
  pages.push(page)
  return page
}

test.afterEach(async ({}, testInfo) => {
  if (testInfo.status !== testInfo.expectedStatus) {
    // Taken here rather than by the runner so the one-time private key the register page
    // shows is masked out of anything that could be published.
    for (const [index, page] of pages.entries()) {
      if (page.isClosed()) continue
      await testInfo.attach(`page-${index + 1}-at-failure`, {
        body: await page.screenshot({ fullPage: true, mask: [page.locator('textarea')] }),
        contentType: 'image/png',
      })
    }
  }
  for (const page of pages.splice(0)) await page.context().close()
})

async function register(page: Page, account: Account) {
  await page.goto('/register')
  await page.getByRole('textbox', { name: /^Username/ }).fill(account.username)
  await page.getByRole('textbox', { name: /^Password/ }).fill(account.password)
  await page.getByRole('textbox', { name: /^Confirm Password/ }).fill(account.password)
  await page.getByRole('textbox', { name: /^Encryption Passphrase/ }).fill(account.passphrase)
  await page.getByRole('textbox', { name: /^Email Address/ }).fill(account.email)

  await page.getByRole('button', { name: 'Send code' }).click()
  await expect(page.getByText('a code is on its way')).toBeVisible()
  let code: string | undefined
  await expect
    .poll(() => (code = takeVerificationCode(account.email)), {
      message: `a verification email for ${account.email}`,
    })
    .toBeTruthy()
  await page.getByRole('textbox', { name: /^Verification Code/ }).fill(code!)

  await page.getByRole('button', { name: 'Register' }).click()
  // Key generation and Argon2id run in the page before the request is even sent.
  await expect(page.getByRole('heading', { name: 'Save Your Private Key' })).toBeVisible({
    timeout: 60_000,
  })
  await page.getByRole('checkbox', { name: /I have saved this private key/ }).check()
  await page.getByRole('link', { name: 'Continue to sign in' }).click()
  await expect(page.getByRole('heading', { name: 'Sign In' })).toBeVisible()
}

async function signIn(page: Page, account: Account) {
  await page.goto('/login')
  await page.getByRole('textbox', { name: 'Username' }).fill(account.username)
  await page.getByRole('textbox', { name: /^Password/ }).fill(account.password)
  await page.getByRole('button', { name: 'Login' }).click()
  await expect(page).toHaveURL(/\/dashboard$/)
  await expect(page.getByRole('heading', { name: 'Your Workspace' })).toBeVisible()
}

async function openMyFiles(page: Page) {
  await page.getByRole('navigation').getByRole('link', { name: 'My Files', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Manage Encrypted Files' })).toBeVisible()
}

/** Download-and-decrypt a row, unlocking the account key on the way, and return the bytes. */
async function downloadDecrypted(page: Page, account: Account): Promise<Buffer> {
  const row = page.getByRole('row').filter({ hasText: fileName })
  await row.getByRole('button', { name: 'Download and decrypt' }).click()

  const unlock = page.getByRole('heading', { name: 'Unlock your files' })
  await expect(unlock).toBeVisible()
  await page.getByRole('textbox', { name: /^Encryption passphrase/ }).fill(account.passphrase)
  const download = page.waitForEvent('download', { timeout: 60_000 })
  await page.getByRole('button', { name: 'Unlock', exact: true }).click()
  await expect(unlock).toBeHidden({ timeout: 60_000 })

  const saved = await download
  expect(saved.suggestedFilename()).toBe(fileName)
  await expect(page.getByText(`Decrypted and saved ${fileName}`)).toBeVisible()
  return readFile(await saved.path())
}

async function signOut(page: Page) {
  await page.getByRole('button', { name: /^Account menu for/ }).hover()
  await page.getByRole('menuitem', { name: 'Log out' }).click()
  await expect(page.getByRole('heading', { name: 'Sign In' })).toBeVisible()
  expect(await page.evaluate(() => localStorage.getItem('access_token'))).toBeNull()
  // The session is gone from this browser: a protected page sends it back to sign in.
  await page.goto('/files')
  await expect(page).toHaveURL(/\/login\?redirect=/)
}

test('a new user encrypts, shares and revokes a file through the pages', async ({ browser }) => {
  const owner = await openPage(browser)
  const recipient = await openPage(browser)

  await test.step('register both accounts through the emailed-code flow', async () => {
    await register(owner, alice)
    await register(recipient, bob)
  })

  await test.step('sign in', async () => {
    await signIn(owner, alice)
  })

  await test.step('encrypt and upload a file', async () => {
    await owner.getByRole('link', { name: /^Upload & Encrypt/ }).click()
    await owner.getByLabel('Select Files').setInputFiles({
      name: fileName,
      mimeType: 'application/octet-stream',
      buffer: fileBytes,
    })
    await owner.getByRole('button', { name: 'Start Encryption' }).click()
    await expect(owner.getByRole('button', { name: 'Encryption Complete' })).toBeVisible({
      timeout: 60_000,
    })
    await owner.getByRole('button', { name: 'View Encrypted Files' }).click()
    await expect(owner.getByRole('row').filter({ hasText: fileName })).toBeVisible()
  })

  await test.step('unlock the account key and download the original bytes', async () => {
    const bytes = await downloadDecrypted(owner, alice)
    expect(bytes.equals(fileBytes), 'the decrypted download equals the uploaded file').toBe(true)
  })

  const recipientField = owner.getByRole('textbox', { name: /their username/i })
  const shareDialog = owner.locator('form').filter({ has: recipientField })

  await test.step('share the file with the second account', async () => {
    const row = owner.getByRole('row').filter({ hasText: fileName })
    await row.getByRole('button', { name: 'Share', exact: true }).click()
    await expect(owner.getByRole('heading', { name: 'Share this file' })).toBeVisible()
    await recipientField.fill(bob.username)
    await shareDialog.getByRole('button', { name: 'Share', exact: true }).click()
    await expect(owner.getByText(`Shared with ${bob.username}`)).toBeVisible({ timeout: 30_000 })
    await expect(owner.getByRole('listitem').filter({ hasText: bob.username })).toBeVisible()
    await owner.getByRole('button', { name: 'Cancel' }).click()
  })

  const sharedTab = recipient.getByRole('button', { name: /^Shared with me/ })
  const sharedRow = recipient.getByRole('row').filter({ hasText: fileName })

  await test.step('the second account sees the file and opens it with its own passphrase', async () => {
    await signIn(recipient, bob)
    await openMyFiles(recipient)
    await sharedTab.click()
    await expect(sharedRow).toContainText(`Shared by ${alice.username}`)
    const bytes = await downloadDecrypted(recipient, bob)
    expect(bytes.equals(fileBytes), "the recipient's download equals the uploaded file").toBe(true)
  })

  await test.step('revoke the share', async () => {
    const row = owner.getByRole('row').filter({ hasText: fileName })
    await row.getByRole('button', { name: 'Share', exact: true }).click()
    const holder = owner.getByRole('listitem').filter({ hasText: bob.username })
    await holder.getByRole('button', { name: 'Revoke' }).click()
    await expect(owner.getByText(`Revoked ${bob.username}'s access`)).toBeVisible()
    await expect(owner.getByText('Nobody yet')).toBeVisible()
    await owner.getByRole('button', { name: 'Cancel' }).click()
  })

  await test.step('the second account no longer sees the file', async () => {
    await recipient.reload()
    await expect(recipient.getByRole('heading', { name: 'Manage Encrypted Files' })).toBeVisible()
    await sharedTab.click()
    await expect(recipient.getByText('No one has shared a file with you yet.')).toBeVisible()
    await expect(sharedRow).toHaveCount(0)
  })

  await test.step('log out', async () => {
    await signOut(owner)
    await signOut(recipient)
  })
})
