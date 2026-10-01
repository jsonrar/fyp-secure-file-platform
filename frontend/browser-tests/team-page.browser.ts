/**
 * The Contact us page: supervisor, team and feedback form render, the supervisor's photo
 * actually loads (the site's CSP only allows images from its own origin, so a hot-linked
 * photo would silently fail), the Monash profile link is right, and a phone does not scroll
 * sideways. Needs no account.
 */
import { expect, test } from '@playwright/test'

const PROFILE = 'https://research.monash.edu/en/persons/asad-malik/'

test('the team page shows the supervisor, the four members and the feedback form', async ({ page }) => {
  await page.goto('/team')

  await expect(page.getByRole('heading', { name: 'Contact us' })).toBeVisible()
  await expect(page.getByTestId('team-feedback').getByRole('button', { name: 'Send feedback' })).toBeVisible()

  const supervisor = page.getByTestId('team-supervisor')
  await expect(supervisor.getByRole('heading', { name: 'Dr. Asad Malik' })).toBeVisible()
  await expect(supervisor).toContainText('Cybersecurity Group Leader')
  await expect(supervisor).toContainText('Malaysia School of Information Technology')
  const link = supervisor.getByRole('link', { name: /View Monash profile/ })
  await expect(link).toHaveAttribute('href', PROFILE)
  await expect(link).toHaveAttribute('rel', /noopener/)

  const photo = supervisor.getByAltText('Portrait of Dr. Asad Malik')
  await photo.scrollIntoViewIfNeeded()
  await expect
    .poll(() => photo.evaluate((img: HTMLImageElement) => img.complete && img.naturalWidth > 0))
    .toBe(true)

  const members = page.getByTestId('team-member')
  await expect(members).toHaveCount(4)
  for (const [name, role] of [
    ['Shuoxun Wen', 'Project Lead'],
    ['Jason Huang', 'Backend and APIs'],
    ['Junyan Li', 'Frontend and Interface'],
    ['Tai Chen', 'Cryptography'],
  ]) {
    const card = members.filter({ hasText: name })
    await expect(card).toContainText(role)
  }
})

test('the team page does not scroll sideways on a phone', async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 740 })
  await page.goto('/team')
  await expect(page.getByTestId('team-members')).toBeVisible()

  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  )
  expect(overflow, 'page is wider than the screen by this many pixels').toBeLessThanOrEqual(0)
})
