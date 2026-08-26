/**
 * Human labels for the audit vocabulary the API actually answers with.
 *
 * The records page compared `log.action` against the literal `'download'`, which no audit
 * entry has ever been. The backend writes `FILE_DOWNLOAD_AUTHORIZED` when a download is
 * served, so the Downloads counter read zero no matter how many files had been downloaded,
 * every event fell through to being counted as a view, and the raw enum name was rendered
 * to the user. Read as "downloads are not being recorded" -- they were, all along.
 */
export type AuditCategory = 'download' | 'view' | 'share' | 'other'

interface AuditActionInfo {
  label: string
  category: AuditCategory
}

const ACTIONS: Record<string, AuditActionInfo> = {
  FILE_UPLOADED: { label: 'Uploaded', category: 'other' },
  FILE_DOWNLOAD_AUTHORIZED: { label: 'Downloaded', category: 'download' },
  FILE_DOWNLOAD_INTEGRITY_FAILED: { label: 'Download blocked: integrity check failed', category: 'download' },
  FILE_INTEGRITY_CHECKED: { label: 'Integrity checked', category: 'view' },
  FILE_SHARED: { label: 'Shared', category: 'share' },
  FILE_ACCESS_REVOKED: { label: 'Access revoked', category: 'share' },
  FILE_DELETED: { label: 'Deleted', category: 'other' },
  RECOVERY_REQUEST_CREATED: { label: 'Recovery requested', category: 'other' },
  RECOVERY_REQUEST_EXECUTED: { label: 'Recovery executed', category: 'other' },
  RECOVERY_REQUEST_CANCELLED: { label: 'Recovery cancelled', category: 'other' },
  KEY_PROTECTION_REWRAPPED: { label: 'Passphrase changed', category: 'other' },
  USER_KEY_ADDED: { label: 'Account key added', category: 'other' },
  ACCOUNT_DELETED: { label: 'Account deleted', category: 'other' },
}

/**
 * An unknown action is titled rather than hidden.
 *
 * The vocabulary grows on the server side, and a record the browser has no label for is
 * still a record of something that happened -- dropping it would be worse than showing
 * `SOMETHING_NEW` as "Something new".
 */
export function auditActionLabel(action: string | undefined): string {
  if (!action) return 'Unknown action'
  const known = ACTIONS[action]
  if (known) return known.label
  return action
    .toLowerCase()
    .replace(/_/g, ' ')
    .replace(/^./, (c) => c.toUpperCase())
}

export function auditActionCategory(action: string | undefined): AuditCategory {
  if (!action) return 'other'
  return ACTIONS[action]?.category ?? 'other'
}

/** Only a served download counts. A blocked one is not an access that happened. */
export function isDownloadAction(action: string | undefined): boolean {
  return action === 'FILE_DOWNLOAD_AUTHORIZED'
}
