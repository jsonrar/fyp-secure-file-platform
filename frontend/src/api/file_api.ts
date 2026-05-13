import { http } from './http'

export const fileApi = {
  listFiles() {
    return http.get('/files')
  },
  upload(file: File) {
    const formData = new FormData()
    formData.append('file', file)
    return http.post('/files/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  integrityCheck(fileId: number) {
    return http.post(`/files/${fileId}/integrity-check`)
  },
}
