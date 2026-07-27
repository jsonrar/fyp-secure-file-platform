import { http } from './http'
import type { AuditLogOut } from './types'

export const auditApi = {
  listLogs() {
    return http.get<{ logs: AuditLogOut[] }>('/audit-logs')
  },
  listFileLogs(fileId: number) {
    return http.get<{ file_id: number; logs: AuditLogOut[] }>(`/audit-logs/file/${fileId}`)
  },
  verifyChain() {
    return http.post<{ status: string }>('/audit-logs/verify-chain')
  },
}
