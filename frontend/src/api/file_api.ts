import { http } from './http'
import type { ApiEnvelope } from './auth_api'
import type { FileListOut, FileOut } from './types'
import type { UploadPayload } from '@/crypto/file_envelope'

export const fileApi = {
  /** Paginated. The rows arrive as `data.items`; `page_size` caps at 100. */
  listFiles(params?: { page?: number; page_size?: number }) {
    return http.get<ApiEnvelope<FileListOut>>('/files', { params })
  },
  getFile(fileId: string) {
    return http.get<ApiEnvelope<FileOut>>(`/files/${fileId}`)
  },

  /**
   * Upload one already-encrypted file.
   *
   * The route takes two multipart parts: `file` carries the ciphertext, and `metadata`
   * carries the JSON envelope describing it. Sending only the file is what produced the
   * bare "422" the upload page used to show -- `metadata` is a required form field, and
   * the browser has no way to fill it in without encrypting first.
   *
   * `Content-Type` is deliberately not set here. The browser must generate the multipart
   * boundary itself; naming the type without a boundary produces a body the server cannot
   * parse.
   */
  uploadEncrypted(payload: UploadPayload) {
    const form = new FormData()
    const ciphertext = new Blob([payload.ciphertext as BlobPart], {
      type: 'application/octet-stream',
    })
    form.append('file', ciphertext, `${payload.metadata.file_id}.ciphertext`)
    form.append('metadata', JSON.stringify(payload.metadata))
    return http.post<ApiEnvelope<FileOut>>('/files/upload', form)
  },

  /** Ciphertext only. The caller decrypts locally; the server never holds the file key. */
  download(fileId: string) {
    return http.post(`/files/${fileId}/download`, null, { responseType: 'arraybuffer' })
  },
  delete(fileId: string) {
    return http.post(`/files/${fileId}/delete`)
  },
  integrityCheck(fileId: string) {
    return http.post(`/files/${fileId}/integrity-check`)
  },
}
