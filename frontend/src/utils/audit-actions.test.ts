import { describe, expect, it } from 'vitest'

import { auditActionCategory, auditActionLabel, isDownloadAction } from './audit-actions'

describe('audit action labels', () => {
  it('counts a served download as a download', () => {
    // The regression: the page compared log.action against the literal 'download', which no
    // audit entry has ever been, so the Downloads counter read zero however many files had
    // been downloaded -- reported as "downloads are not being recorded".
    expect(isDownloadAction('FILE_DOWNLOAD_AUTHORIZED')).toBe(true)
    expect(isDownloadAction('download')).toBe(false)
  })

  it('does not count a blocked download as an access that happened', () => {
    expect(isDownloadAction('FILE_DOWNLOAD_INTEGRITY_FAILED')).toBe(false)
  })

  it('names the actions a user recognises instead of the enum', () => {
    expect(auditActionLabel('FILE_DOWNLOAD_AUTHORIZED')).toBe('Downloaded')
    expect(auditActionLabel('FILE_SHARED')).toBe('Shared')
    expect(auditActionLabel('FILE_UPLOADED')).toBe('Uploaded')
  })

  it('still shows an action it has no label for', () => {
    // The vocabulary grows server-side. A record the browser cannot name is still a record
    // of something that happened, and dropping it would be worse than titling it.
    expect(auditActionLabel('SOMETHING_ENTIRELY_NEW')).toBe('Something entirely new')
  })

  it('handles a log row with no action rather than rendering undefined', () => {
    expect(auditActionLabel(undefined)).toBe('Unknown action')
    expect(auditActionCategory(undefined)).toBe('other')
    expect(isDownloadAction(undefined)).toBe(false)
  })

  it('groups sharing actions together', () => {
    expect(auditActionCategory('FILE_SHARED')).toBe('share')
    expect(auditActionCategory('FILE_ACCESS_REVOKED')).toBe('share')
  })
})
