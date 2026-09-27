import { http } from './http'
import type { ApiEnvelope } from './auth_api'
import type { FileListOut, FileOut } from './types'
import type { UploadPayload } from '@/crypto/file_envelope'

export const fileApi = {
  /**
   * Paginated. The rows arrive as `data.items`; `page_size` caps at 100.
   *
   * `search` is a case-insensitive substring of the original filename, matched by the
   * server across every page. Filtering in the browser can only ever see the page it
   * already holds, which is why the box used to answer "no results" for files that
   * existed on another page.
   */
  listFiles(params?: {
    page?: number
    page_size?: number
    search?: string
    /** List only owned files on this shelf. */
    shelf_id?: string
    /** List only owned files with no shelf (the root). */
    root_only?: boolean
  }) {
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

  /** Verified ciphertext only. The caller can save it as-is or decrypt it locally. */
  download(fileId: string) {
    return http.post(`/files/${fileId}/download`, null, { responseType: 'arraybuffer' })
  },
  delete(fileId: string) {
    return http.post(`/files/${fileId}/delete`)
  },
  /** Move an owned file onto a shelf, or back to the root when `shelfId` is null. */
  move(fileId: string, shelfId: string | null) {
    return http.post<ApiEnvelope<FileOut>>(`/files/${fileId}/move`, { shelf_id: shelfId })
  },
  integrityCheck(fileId: string) {
    return http.post(`/files/${fileId}/integrity-check`)
  },
}
