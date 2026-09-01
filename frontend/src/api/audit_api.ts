import { http } from './http'
import type { ApiEnvelope, AuditLogOut } from './types'

export interface AuditLogPage {
  logs: AuditLogOut[]
  limit: number
  offset: number
  has_more: boolean
}

// Every audit route answers through the same `ok(...)` envelope as the rest of the API.
// These three declared the inner payload as if it arrived bare, so `unwrapData` was
// reaching through a wrapper TypeScript had been told was not there.
export const auditApi = {
  /**
   * One page of the caller's audit trail.
   *
   * `limit` caps at 100 server-side and defaults to 50, and the response says whether more
   * remain. Callers that summarise the trail have to page: totals taken from the first
   * page are totals of the last fifty events, which is not what a stat card claims to be.
   */
  listLogs(params?: { limit?: number; offset?: number }) {
    return http.get<ApiEnvelope<AuditLogPage>>('/audit-logs', { params })
  },
  listFileLogs(fileId: string) {
    return http.get<ApiEnvelope<{ file_id: string; logs: AuditLogOut[] }>>(
      `/audit-logs/file/${fileId}`,
    )
  },
  /**
   * ADMIN only. Recomputes every hash in the table, so a non-admin gets a 403 -- which is a
   * permission answer, not a finding about the chain.
   */
  verifyChain() {
    return http.post<
      ApiEnvelope<{
        status: string
        valid: boolean
        checked_entries: number
        first_invalid_position: number | null
      }>
    >('/audit-logs/verify-chain')
  },
}
