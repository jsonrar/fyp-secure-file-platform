/**
 * Encrypted upload: turn a browser File into what `POST /files/upload` accepts.
 *
 * The plaintext never leaves this module. It is read into memory, encrypted under a fresh
 * data encryption key, and only the ciphertext and the envelope metadata are handed to the
 * API layer.
 */

import { fileApi } from '@/api/file_api'
import { keyApi } from '@/api/key_api'
import { recoveryApi } from '@/api/recovery_api'

import { buildUploadPayload, encryptFile, type UploadPayload } from './file_envelope'
import {
  DEFAULT_ENCRYPTION_ALGORITHM,
  type EncryptionAlgorithm,
  publicKeyFingerprint,
} from './primitives'

/** Mirrors the backend `MAX_UPLOAD_SIZE_BYTES` default so oversize files fail before work. */
export const MAX_UPLOAD_BYTES = 500 * 1024 * 1024

/**
 * `File.type` is advisory: browsers leave it empty for unknown extensions, and the API
 * requires a well-formed media type. Fall back rather than sending something it will reject.
 */
export const DEFAULT_MIME_TYPE = 'application/octet-stream'

/** The public keys an upload wraps its file key to. No private key is involved. */
export interface UploadRecipients {
  ownerKeyId: string
  ownerPublicKeyPem: string
  recoveryKeyId: string
  recoveryPublicKeyPem: string
  /** Locally recomputed, for the caller to pin. Never taken from the API response. */
  recoveryKeyFingerprint: string
}

export function resolveMimeType(type: string | undefined): string {
  const normalized = (type ?? '').trim().toLowerCase()
  // Browsers also report placeholder values for files they cannot classify.
  if (normalized === '' || normalized === 'unknown') {
    return DEFAULT_MIME_TYPE
  }
  return normalized
}

/**
 * Finder and other file pickers can preserve invisible whitespace at either edge of a
 * filename. The API deliberately rejects that ambiguous form, so canonicalise only those
 * edges before the name is authenticated as AAD. Ordinary spaces inside the name remain.
 */
export function resolveUploadFilename(name: string): string {
  return name.normalize('NFC').trim()
}

/**
 * Fetch the owner and recovery public keys.
 *
 * The recovery fingerprint is recomputed from the PEM rather than read from the response
 * field. A server that substitutes the recovery key can substitute the field describing it
 * just as easily, and this is the one wrapping no client can ever verify.
 */
export async function fetchUploadRecipients(): Promise<UploadRecipients> {
  const [bundle, recovery] = await Promise.all([keyApi.myBundle(), recoveryApi.getPublicKey()])
  const ownerKey = bundle.data.data.key
  const recoveryKey = recovery.data.data

  if (recoveryKey.status !== 'ACTIVE') {
    throw new Error('The recovery key is not active. Ask an administrator to register one.')
  }

  return {
    ownerKeyId: ownerKey.key_id,
    ownerPublicKeyPem: ownerKey.public_key_pem,
    recoveryKeyId: recoveryKey.key_id,
    recoveryPublicKeyPem: recoveryKey.public_key_pem,
    recoveryKeyFingerprint: await publicKeyFingerprint(recoveryKey.public_key_pem),
  }
}

/** The subset of `File` this module needs, so tests do not have to build a real one. */
export interface UploadableFile {
  name: string
  size: number
  type?: string
  arrayBuffer(): Promise<ArrayBuffer>
}

/**
 * Encrypt one file and assemble its upload payload. Performs no network calls.
 *
 * `encryptFile` self-tests its own output before this returns, so a payload produced here
 * is known to decrypt back to the exact input bytes.
 */
export async function prepareUpload(params: {
  file: UploadableFile
  recipients: UploadRecipients
  algorithm?: EncryptionAlgorithm
}): Promise<UploadPayload> {
  const { file, recipients } = params

  if (file.size > MAX_UPLOAD_BYTES) {
    throw new RangeError(
      `${file.name} is ${file.size} bytes; the upload limit is ${MAX_UPLOAD_BYTES} bytes`,
    )
  }

  const plaintext = new Uint8Array(await file.arrayBuffer())
  const envelope = await encryptFile({
    plaintext,
    originalFilename: resolveUploadFilename(file.name),
    mimeType: resolveMimeType(file.type),
    algorithm: params.algorithm ?? DEFAULT_ENCRYPTION_ALGORITHM,
  })

  return buildUploadPayload({
    envelope,
    ownerKeyId: recipients.ownerKeyId,
    ownerPublicKeyPem: recipients.ownerPublicKeyPem,
    recoveryKeyId: recipients.recoveryKeyId,
    recoveryPublicKeyPem: recipients.recoveryPublicKeyPem,
  })
}

export interface UploadResult {
  fileId: string
  originalFilename: string
  plaintextSize: number
  ciphertextSize: number
  encryptionAlgorithm: string
  recoveryKeyFingerprint: string
}

/** Encrypt and upload one file. Fetches the recipient keys if the caller has not. */
export async function encryptAndUpload(
  file: UploadableFile,
  recipients?: UploadRecipients,
  algorithm?: EncryptionAlgorithm,
): Promise<UploadResult> {
  const resolved = recipients ?? (await fetchUploadRecipients())
  const payload = await prepareUpload({ file, recipients: resolved, algorithm })

  await fileApi.uploadEncrypted(payload)

  return {
    fileId: payload.metadata.file_id,
    originalFilename: payload.metadata.original_filename,
    plaintextSize: payload.metadata.plaintext_size,
    ciphertextSize: payload.ciphertext.length,
    encryptionAlgorithm: payload.metadata.encryption_algorithm,
    recoveryKeyFingerprint: payload.recoveryKeyFingerprint,
  }
}
