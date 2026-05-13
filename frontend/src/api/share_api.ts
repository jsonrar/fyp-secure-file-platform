import { http } from './http'

export const shareApi = {
  shareFile(fileId: number, payload: unknown) {
    return http.post(`/files/${fileId}/share`, payload)
  },
  revokeAccess(fileId: number, payload: unknown) {
    return http.post(`/files/${fileId}/revoke`, payload)
  },
}
