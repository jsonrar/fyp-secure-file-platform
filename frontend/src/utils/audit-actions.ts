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
  // Account-level events now have a group of their own on the records page, so they are
  // worth naming properly rather than leaving to the title-case fallback.
  AUTH_REGISTERED: { label: 'Account created', category: 'other' },
  AUTH_LOGIN_SUCCEEDED: { label: 'Signed in', category: 'other' },
  AUTH_LOGIN_FAILED: { label: 'Sign-in failed', category: 'other' },
  AUTH_LOGGED_OUT: { label: 'Signed out', category: 'other' },
  AUTH_PASSWORD_CHANGED: { label: 'Password changed', category: 'other' },
  AUTH_PASSWORD_CHANGE_FAILED: { label: 'Password change failed', category: 'other' },
  AUTH_PASSWORD_RESET: { label: 'Password reset', category: 'other' },
  AUTH_SESSION_REVOKED: { label: 'Session revoked', category: 'other' },
  AUTH_ALL_SESSIONS_REVOKED: { label: 'All sessions signed out', category: 'other' },
  AUTH_SESSION_EXPIRED: { label: 'Session expired', category: 'other' },
  AUTH_SESSION_REFRESHED: { label: 'Session renewed', category: 'other' },
  AUTH_REFRESH_REJECTED: { label: 'Session renewal rejected', category: 'other' },
  AUTH_REFRESH_REPLAY_DETECTED: { label: 'Reused session token detected', category: 'other' },
  AUTH_VERIFICATION_CODE_SENT: { label: 'Verification code sent', category: 'other' },
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

/** The minimum of an audit row this module needs. */
interface AuditSubject {
  resource_type: string
  resource_id: string | null
}

/**
 * The file an audit row is about, or null when it is about the account itself.
 *
 * The API identifies the subject as `resource_type` + `resource_id`; it has never sent a
 * `file_id`, which is what the page used to read. Because the field was optional in the
 * frontend type, every row resolved to `undefined` and landed in one nameless group.
 *
 * SHARE rows count as file rows: `resource_id` is the file being shared, and a share belongs
 * in that file's history rather than off on its own.
 */
export function auditSubjectFileId(log: AuditSubject): string | null {
  if (log.resource_type !== 'FILE' && log.resource_type !== 'SHARE') return null
  return log.resource_id || null
}
