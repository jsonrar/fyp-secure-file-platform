import { describe, expect, it } from 'vitest'

import {
  auditActionCategory,
  auditActionLabel,
  auditSubjectFileId,
  isDownloadAction,
  isShareAction,
} from './audit-actions'

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

  it('names the account events that share the records page', () => {
    // They have their own group now, so "Auth login succeeded" from the fallback is no
    // longer good enough.
    expect(auditActionLabel('AUTH_LOGIN_SUCCEEDED')).toBe('Signed in')
    expect(auditActionLabel('AUTH_LOGIN_FAILED')).toBe('Sign-in failed')
    expect(auditActionLabel('AUTH_REFRESH_REPLAY_DETECTED')).toBe('Reused session token detected')
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

describe('auditSubjectFileId', () => {
  it('reads the file from resource_type and resource_id', () => {
    // The regression: the page read `log.file_id`, which the API has never sent. Every row
    // resolved to undefined, so the whole history collapsed into one nameless group.
    expect(
      auditSubjectFileId({ resource_type: 'FILE', resource_id: 'f5ba34ea' }),
    ).toBe('f5ba34ea')
  })

  it('files a share under the file it is about', () => {
    // resource_id on a SHARE row is the file, and a share belongs in that file's history
    // rather than in a group of its own.
    expect(
      auditSubjectFileId({ resource_type: 'SHARE', resource_id: 'f5ba34ea' }),
    ).toBe('f5ba34ea')
  })

  it('treats an account event as belonging to no file', () => {
    // Signing in and closing an account are not file history; grouping them under a file id
    // they never had is what produced the "Unknown file" heading.
    expect(auditSubjectFileId({ resource_type: 'USER', resource_id: 'some-user' })).toBeNull()
  })

  it('does not invent a file when the id is missing', () => {
    expect(auditSubjectFileId({ resource_type: 'FILE', resource_id: null })).toBeNull()
    expect(auditSubjectFileId({ resource_type: 'FILE', resource_id: '' })).toBeNull()
  })
})

describe('isShareAction', () => {
  it('counts granting and withdrawing access', () => {
    expect(isShareAction('FILE_SHARED')).toBe(true)
    expect(isShareAction('FILE_ACCESS_REVOKED')).toBe(true)
  })

  it('does not count anything else as a change to who can reach the file', () => {
    // The stat this feeds used to be "Total Views", which counted every non-download event
    // -- uploads, shares, even sign-ins -- as somebody viewing a file. Nothing did.
    expect(isShareAction('FILE_UPLOADED')).toBe(false)
    expect(isShareAction('FILE_DOWNLOAD_AUTHORIZED')).toBe(false)
    expect(isShareAction('AUTH_LOGIN_SUCCEEDED')).toBe(false)
    expect(isShareAction(undefined)).toBe(false)
  })
})
