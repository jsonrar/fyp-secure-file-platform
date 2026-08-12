import { http } from './http'

export const shareApi = {
  shareFile(fileId: string, payload: unknown) {
    return http.post(`/files/${fileId}/share`, payload)
  },
  revokeAccess(fileId: string, payload: unknown) {
    return http.post(`/files/${fileId}/revoke`, payload)
  },
}
