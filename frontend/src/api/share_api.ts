import { http } from './http'
import type { ApiEnvelope } from './auth_api'

/**
 * What `POST /files/{id}/share` actually requires.
 *
 * This was `unknown`, and the dialog sent `{ target_username }` -- three required fields
 * short, plus one the strict schema forbids. Every share attempt was a 422 that the UI
 * reported as "Share request sent".
 */
export interface ShareFilePayload {
  target_user_id: string
  target_key_id: string
  /** The file's DEK, rewrapped to the recipient's public key. Base64. */
  wrapped_file_key: string
  can_download?: boolean
  can_share?: boolean
}

export interface ShareFileResult {
  file_id: string
  target_user_id: string
  target_key_id: string
  status: string
  created: boolean
}

export interface RevokeAccessPayload {
  target_user_id: string
}

export const shareApi = {
  shareFile(fileId: string, payload: ShareFilePayload) {
    return http.post<ApiEnvelope<ShareFileResult>>(`/files/${fileId}/share`, payload)
  },
  revokeAccess(fileId: string, payload: RevokeAccessPayload) {
    return http.post(`/files/${fileId}/revoke`, payload)
  },
}
