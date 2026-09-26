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
