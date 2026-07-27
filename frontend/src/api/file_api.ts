import { http } from './http'
import type { FileOut } from './types'

export const fileApi = {
  listFiles() {
    return http.get<{ files: FileOut[] }>('/files')
  },
  getFile(fileId: number) {
    return http.get<FileOut>(`/files/${fileId}`)
  },
  upload(file: File) {
    const formData = new FormData()
    formData.append('file', file)
    return http.post('/files/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  download(fileId: number) {
    return http.post(`/files/${fileId}/download`)
  },
  delete(fileId: number) {
    return http.delete(`/files/${fileId}`)
  },
  integrityCheck(fileId: number) {
    return http.post(`/files/${fileId}/integrity-check`)
  },
}
