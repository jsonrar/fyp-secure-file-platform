export interface ApiEnvelope<T> {
  success: boolean
  status: string
  message: string
  data: T
  code: number
}

export interface FileOut {
  file_id: number
  original_filename: string
  file_size: number
  status: string
}

export interface AuditLogOut {
  log_id?: number
  file_id?: number
  action?: string
  actor_username?: string
  created_at?: string
  device?: string
  location?: string
}

export function unwrapData<T>(response: { data: ApiEnvelope<T> }): T {
  return response.data.data
}

export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`
}

export function mapFileStatus(status: string): 'verified' | 'modified' | 'pending' {
  const normalized = status.toUpperCase()
  if (normalized === 'VALID' || normalized === 'VERIFIED') return 'verified'
  if (normalized === 'MODIFIED' || normalized === 'INVALID') return 'modified'
  return 'pending'
}
