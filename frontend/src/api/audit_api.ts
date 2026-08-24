import { http } from './http'
import type { ApiEnvelope, AuditLogOut } from './types'

// Every audit route answers through the same `ok(...)` envelope as the rest of the API.
// These three declared the inner payload as if it arrived bare, so `unwrapData` was
// reaching through a wrapper TypeScript had been told was not there.
export const auditApi = {
  listLogs() {
    return http.get<ApiEnvelope<{ logs: AuditLogOut[] }>>('/audit-logs')
  },
  listFileLogs(fileId: string) {
    return http.get<ApiEnvelope<{ file_id: string; logs: AuditLogOut[] }>>(
      `/audit-logs/file/${fileId}`,
    )
  },
  verifyChain() {
    return http.post<ApiEnvelope<{ status: string }>>('/audit-logs/verify-chain')
  },
}
