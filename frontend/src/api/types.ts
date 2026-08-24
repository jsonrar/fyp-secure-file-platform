export interface ApiEnvelope<T> {
  success: boolean
  status: string
  message: string
  data: T
  code: number
}

/** One row of `GET /files`. Mirrors the backend `FileSummaryOut`. */
export interface FileSummaryOut {
  file_id: string
  original_filename: string
  /** Size of the original file. Equal to the ciphertext size under AES-GCM. */
  plaintext_size: number
  /** Size of the stored ciphertext, excluding the detached authentication tag. */
  ciphertext_size: number
  mime_type: string | null
  encryption_algorithm: string
  status: string
  owner: boolean
  created_at: string
  updated_at: string
}

/** `GET /files/{id}` adds the envelope needed to decrypt. */
export interface FileOut extends FileSummaryOut {
  crypto_envelope: FileCryptoEnvelopeOut
}

/** The envelope fields a client needs to unwrap the file key and decrypt. */
export interface FileCryptoEnvelopeOut {
  encryption_algorithm: 'AES-256-GCM'
  envelope_version: number
  aad_version: number
  nonce: string
  auth_tag: string
  key_id: string
  key_wrapping_algorithm: 'RSA-OAEP-SHA256'
  wrapped_file_key: string
  encrypted_manifest: string | null
}

/** `GET /files` is paginated: the rows live under `items`, not `files`. */
export interface FileListOut {
  items: FileSummaryOut[]
  page: number
  page_size: number
  total: number
}

export interface AuditLogOut {
  log_id?: number
  file_id?: string
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

export type FileBadge = 'verified' | 'modified' | 'pending'

/**
 * Map an *integrity check* result onto a badge.
 *
 * The vocabulary here is the one `POST /files/{id}/integrity-check` answers with:
 * `VALID`, `MODIFIED`, `MISSING`, `ERROR`. It is not the vocabulary of `files.status`.
 */
export function mapFileStatus(status: string): FileBadge {
  const normalized = status.toUpperCase()
  if (normalized === 'VALID' || normalized === 'VERIFIED') return 'verified'
  if (normalized === 'MODIFIED' || normalized === 'INVALID') return 'modified'
  return 'pending'
}

/**
 * Map a *file lifecycle* status onto a badge.
 *
 * `GET /files` reports `files.status` — `ACTIVE`, `CORRUPTED`, `DELETED` — which shares no
 * word with the integrity vocabulary above. Running it through `mapFileStatus` sent every
 * value down the fallback branch, so a healthy file and a file the server had positively
 * marked as damaged both rendered as an identical grey "Pending". The two lookups are kept
 * apart because they answer different questions about different fields.
 */
export function mapFileLifecycle(status: string): FileBadge {
  const normalized = status.toUpperCase()
  if (normalized === 'ACTIVE') return 'verified'
  if (normalized === 'CORRUPTED') return 'modified'
  return 'pending'
}
