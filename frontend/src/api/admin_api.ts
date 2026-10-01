import { http } from './http'
import type { ApiEnvelope } from './types'

export interface AdminUserOut {
  user_id: string
  username: string
  role: string
  status: string
  created_at: string
  last_login_at: string | null
}

export interface AdminUserList {
  users: AdminUserOut[]
  limit: number
  offset: number
  has_more: boolean
}

export interface AdminFileOut {
  file_id: string
  owner_id: string
  owner_username: string
  original_filename: string
  mime_type: string | null
  file_size: number
  encrypted_size: number | null
  status: string
  created_at: string
  updated_at: string
}

export interface AdminFileList {
  files: AdminFileOut[]
  limit: number
  offset: number
  has_more: boolean
}

export interface AdminStats {
  generated_at: string
  users: {
    total: number
    active: number
    disabled: number
    deleted: number
    administrators: number
    created_last_7_days: number
    signed_in_last_24_hours: number
  }
  files: {
    total: number
    active: number
    corrupted: number
    deleted: number
    uploaded_last_24_hours: number
    original_bytes: number
    stored_bytes: number
    by_algorithm: Record<string, number>
  }
  shares: { active_shares: number; files_shared: number }
  integrity: { checks_last_24_hours: number; failed_checks_last_24_hours: number }
  recovery: { pending_requests: number }
  audit: {
    events_total: number
    events_last_24_hours: number
    failures_last_24_hours: number
    recent_failures: {
      action: string
      result: string
      created_at: string
      actor_username: string | null
    }[]
  }
}

export interface AdminDamagedFile {
  file_id: string
  owner_username: string
  original_filename: string
  status: string
  last_result: string | null
  last_message: string | null
  last_checked_at: string | null
}

export interface AdminIntegrityReport {
  generated_at: string
  coverage: {
    candidates: number
    never_checked: number
    checked_last_24_hours: number
    last_sweep_at: string | null
  }
  damaged: AdminDamagedFile[]
  has_more: boolean
}

export interface AdminIntegrityScan {
  scanned: number
  valid: number
  damaged: number
  candidates: number
  stopped_early: boolean
  damaged_file_ids: string[]
}

export interface AdminUserStatusResult {
  user_id: string
  status: string
  changed: boolean
  revoked_sessions: number
}

export const adminApi = {
  listUsers(params?: { limit?: number; offset?: number }) {
    return http.get<ApiEnvelope<AdminUserList>>('/admin/users', { params })
  },
  /** Counts only: how big the platform is and how healthy. No names, keys or addresses. */
  stats() {
    return http.get<ApiEnvelope<AdminStats>>('/admin/stats')
  },
  /** Which files are damaged, and how much of the store has been verified at all. */
  integrityReport() {
    return http.get<ApiEnvelope<AdminIntegrityReport>>('/admin/integrity')
  },
  /** Verify a bounded batch of stored objects now, least recently checked first. */
  scanIntegrity() {
    return http.post<ApiEnvelope<AdminIntegrityScan>>('/admin/integrity/scan')
  },
  listFiles(params?: { limit?: number; offset?: number }) {
    return http.get<ApiEnvelope<AdminFileList>>('/admin/files', { params })
  },
  disableUser(userId: string) {
    return http.post<ApiEnvelope<AdminUserStatusResult>>(`/admin/users/${userId}/disable`)
  },
  enableUser(userId: string) {
    return http.post<ApiEnvelope<AdminUserStatusResult>>(`/admin/users/${userId}/enable`)
  },
}
