/**
 * File encryption envelope.
 *
 * A file is encrypted once, under one random data encryption key (DEK), and that same DEK is
 * wrapped separately to every party allowed to open it: the owner, the recovery key, and
 * later each share recipient. The server stores ciphertext and wrapped keys; it never holds
 * a DEK and therefore never computes this AAD or authenticates this tag.
 *
 * That last point makes the layout below a one-way commitment. No server-side check can
 * catch an implementation that builds these bytes differently -- it will simply produce
 * files that nobody can decrypt. Any second implementation must reproduce `fileContentAad`
 * byte for byte; `docs/crypto/FILE_ENVELOPE.md` is the normative description and
 * `docs/crypto/test_vectors.json` locks it.
 */

import {
  asciiBytes,
  concatBytes,
  frame,
  toBase64,
  u32,
  u64,
  u8,
  utf8Bytes,
  uuidToBytes,
} from './encoding'
import {
  AES_GCM_NONCE_BYTES,
  AES_KEY_BYTES,
  aesGcmDecryptDetached,
  aesGcmEncryptDetached,
  importAesGcmKey,
  importRsaOaepPublicKey,
  publicKeyFingerprint,
  randomBytes,
  randomUuid,
  rsaOaepUnwrap,
  rsaOaepWrap,
} from './primitives'

export const ENVELOPE_VERSION = 1
export const AAD_VERSION = 1
export const ENCRYPTION_ALGORITHM = 'AES-256-GCM'
export const KEY_WRAPPING_ALGORITHM = 'RSA-OAEP-SHA256'

const AAD_LABEL = 'FYP-FILE-CONTENT'
const MAX_FILENAME_LENGTH = 255
const MIME_TYPE_PATTERN =
  /^[A-Za-z0-9][A-Za-z0-9!#$&^_.+-]{0,126}\/[A-Za-z0-9][A-Za-z0-9!#$&^_.+-]{0,126}$/

/** The file facts every party who can decrypt the file agrees on. */
export interface FileIdentity {
  fileId: string
  originalFilename: string
  plaintextSize: number
  mimeType: string
  envelopeVersion?: number
  aadVersion?: number
  encryptionAlgorithm?: string
}

type NormalizedIdentity = Required<FileIdentity>

/**
 * Apply the same normalization and rejection rules as `FileUploadMetadata`.
 *
 * Doing this locally is not duplication for its own sake: a filename that the client hashes
 * in one form and the server stores in another produces an AAD mismatch that only surfaces
 * as a failed decryption later, long after the upload appeared to succeed.
 */
export function normalizeIdentity(identity: FileIdentity): NormalizedIdentity {
  const filename = identity.originalFilename.normalize('NFC')
  if (identity.originalFilename.length > MAX_FILENAME_LENGTH || filename.length < 1) {
    throw new RangeError('original_filename must be between 1 and 255 characters')
  }
  if (filename !== filename.trim()) {
    throw new TypeError('original_filename must not have surrounding whitespace')
  }
  if (filename === '.' || filename === '..') {
    throw new TypeError('original_filename is not a valid filename')
  }
  if (/[/\\]/.test(filename)) {
    throw new TypeError('original_filename must not contain path separators')
  }
  if (/\p{Cc}/u.test(filename)) {
    throw new TypeError('original_filename must not contain control characters')
  }
  if (filename.endsWith(' ') || filename.endsWith('.')) {
    throw new TypeError('original_filename must not end with a space or period')
  }

  const mimeType = identity.mimeType.toLowerCase()
  if (mimeType.length < 3 || mimeType.length > 150 || !MIME_TYPE_PATTERN.test(mimeType)) {
    throw new TypeError('mime_type must be a valid media type without parameters')
  }

  if (!Number.isSafeInteger(identity.plaintextSize) || identity.plaintextSize < 0) {
    throw new RangeError('plaintext_size must be a non-negative integer')
  }

  return {
    fileId: identity.fileId,
    originalFilename: filename,
    plaintextSize: identity.plaintextSize,
    mimeType,
    envelopeVersion: identity.envelopeVersion ?? ENVELOPE_VERSION,
    aadVersion: identity.aadVersion ?? AAD_VERSION,
    encryptionAlgorithm: identity.encryptionAlgorithm ?? ENCRYPTION_ALGORITHM,
  }
}

/**
 * AAD-3: the additional authenticated data covering one file's ciphertext.
 *
 * ```
 * ascii("FYP-FILE-CONTENT") || 0x00 || u8(aad_version)
 *   || uuid16(file_id)
 *   || u32(envelope_version)
 *   || frame(ascii(encryption_algorithm))
 *   || u64(plaintext_size)
 *   || frame(utf8_nfc(original_filename))
 *   || frame(ascii(lowercase(mime_type)))
 * ```
 *
 * Every field is identical for the owner and for each share recipient, which is the binding
 * constraint: they all decrypt the same ciphertext with the same DEK. Nothing per-recipient
 * may appear here -- not `key_id`, not `wrapped_file_key`, not grant state -- because the
 * envelope the API returns carries the *caller's* key id, so including it would make shared
 * files undecryptable for everyone but the owner.
 *
 * The filename, MIME type and size are bound deliberately. They are cleartext columns the
 * server could otherwise rewrite, serving a recipient a document labelled as something it is
 * not. Binding them turns such an edit into a decryption failure, at the cost of making the
 * three fields immutable for the lifetime of the ciphertext.
 */
export function fileContentAad(identity: FileIdentity): Uint8Array {
  const normalized = normalizeIdentity(identity)
  return concatBytes(
    asciiBytes(AAD_LABEL),
    u8(0),
    u8(normalized.aadVersion),
    uuidToBytes(normalized.fileId),
    u32(normalized.envelopeVersion),
    frame(asciiBytes(normalized.encryptionAlgorithm)),
    u64(normalized.plaintextSize),
    frame(utf8Bytes(normalized.originalFilename)),
    frame(asciiBytes(normalized.mimeType)),
  )
}

export interface EncryptedFileEnvelope {
  identity: NormalizedIdentity
  /** The raw DEK. It must stay readable to be wrapped, then be discarded with the session. */
  dek: Uint8Array
  nonce: Uint8Array
  ciphertext: Uint8Array
  authTag: Uint8Array
  aad: Uint8Array
}

/**
 * Encrypt with caller-supplied key material.
 *
 * Exposed for reproducible test vectors. Production code calls {@link encryptFile}, which
 * generates fresh material: reusing a (DEK, nonce) pair under GCM discloses the XOR of both
 * plaintexts and allows forgery through authentication-key recovery.
 */
export async function encryptFileWithMaterial(params: {
  plaintext: Uint8Array
  identity: FileIdentity
  dek: Uint8Array
  nonce: Uint8Array
}): Promise<EncryptedFileEnvelope> {
  const { plaintext, dek, nonce } = params
  const identity = normalizeIdentity(params.identity)

  if (dek.length !== AES_KEY_BYTES) {
    throw new RangeError(`DEK must be ${AES_KEY_BYTES} bytes`)
  }
  if (plaintext.length !== identity.plaintextSize) {
    throw new RangeError(
      `plaintext_size ${identity.plaintextSize} does not match the ${plaintext.length}-byte plaintext`,
    )
  }

  const aad = fileContentAad(identity)
  const key = await importAesGcmKey(dek)
  const { ciphertext, authTag } = await aesGcmEncryptDetached({ key, nonce, plaintext, aad })

  // file_service rejects an upload whose ciphertext length differs from plaintext_size.
  // Catching it here costs nothing and turns a confusing 422 into a local failure.
  if (ciphertext.length !== identity.plaintextSize) {
    throw new Error('AES-GCM ciphertext length must equal plaintext_size once the tag is detached')
  }

  return { identity, dek, nonce, ciphertext, authTag, aad }
}

/**
 * Encrypt a file under a fresh DEK and nonce, then verify the result round trips.
 *
 * The self-test is mandatory rather than defensive. The server cannot check that this
 * ciphertext decrypts to anything, so a client that writes a well-formed but unopenable
 * envelope produces a file that is lost the moment the plaintext is discarded.
 */
export async function encryptFile(params: {
  plaintext: Uint8Array
  originalFilename: string
  mimeType: string
  fileId?: string
}): Promise<EncryptedFileEnvelope> {
  const identity: FileIdentity = {
    fileId: params.fileId ?? randomUuid(),
    originalFilename: params.originalFilename,
    plaintextSize: params.plaintext.length,
    mimeType: params.mimeType,
  }

  const envelope = await encryptFileWithMaterial({
    plaintext: params.plaintext,
    identity,
    dek: randomBytes(AES_KEY_BYTES),
    nonce: randomBytes(AES_GCM_NONCE_BYTES),
  })

  const roundTripped = await decryptFile({
    identity: envelope.identity,
    dek: envelope.dek,
    nonce: envelope.nonce,
    ciphertext: envelope.ciphertext,
    authTag: envelope.authTag,
  })
  if (roundTripped.length !== params.plaintext.length) {
    throw new Error('Encryption self-test failed: round-tripped length differs')
  }
  for (let i = 0; i < roundTripped.length; i += 1) {
    if (roundTripped[i] !== params.plaintext[i]) {
      throw new Error(`Encryption self-test failed: byte ${i} differs after round trip`)
    }
  }

  return envelope
}

/** Decrypt and authenticate a file. Throws `AuthenticationFailure` if anything was altered. */
export async function decryptFile(params: {
  identity: FileIdentity
  dek: Uint8Array
  nonce: Uint8Array
  ciphertext: Uint8Array
  authTag: Uint8Array
}): Promise<Uint8Array> {
  const aad = fileContentAad(params.identity)
  const key = await importAesGcmKey(params.dek)
  return aesGcmDecryptDetached({
    key,
    nonce: params.nonce,
    ciphertext: params.ciphertext,
    authTag: params.authTag,
    aad,
  })
}

/** Wrap a DEK to a recipient's PEM public key with RSA-OAEP-SHA256. */
export async function wrapDekTo(publicKeyPem: string, dek: Uint8Array): Promise<Uint8Array> {
  if (dek.length !== AES_KEY_BYTES) {
    throw new RangeError(`DEK must be ${AES_KEY_BYTES} bytes`)
  }
  return rsaOaepWrap(await importRsaOaepPublicKey(publicKeyPem), dek)
}

/** Unwrap a DEK with the holder's private key. */
export async function unwrapDek(privateKey: CryptoKey, wrapped: Uint8Array): Promise<Uint8Array> {
  const dek = await rsaOaepUnwrap(privateKey, wrapped)
  if (dek.length !== AES_KEY_BYTES) {
    throw new Error(`Unwrapped DEK is ${dek.length} bytes, expected ${AES_KEY_BYTES}`)
  }
  return dek
}

/** The JSON metadata part of a `POST /files` multipart upload. */
export interface UploadMetadata {
  file_id: string
  original_filename: string
  plaintext_size: number
  mime_type: string
  encryption_algorithm: string
  envelope_version: number
  aad_version: number
  nonce: string
  auth_tag: string
  owner_key_id: string
  key_wrapping_algorithm: string
  wrapped_file_key: string
  recovery_key_id: string
  recovery_wrapped_file_key: string
}

export interface UploadPayload {
  metadata: UploadMetadata
  ciphertext: Uint8Array
  /**
   * The recovery public key's fingerprint, recomputed locally.
   *
   * Surface this to the user and refuse to upload if it changes without an out-of-band
   * announcement. The recovery wrapping is the one envelope a client cannot self-test -- the
   * recovery private key is offline -- so a substituted recovery key would hand the server a
   * decryptable copy of every DEK, and nothing would notice until a recovery was attempted.
   */
  recoveryKeyFingerprint: string
}

/** Wrap the DEK to the owner and recovery keys and assemble the upload payload. */
export async function buildUploadPayload(params: {
  envelope: EncryptedFileEnvelope
  ownerKeyId: string
  ownerPublicKeyPem: string
  recoveryKeyId: string
  recoveryPublicKeyPem: string
}): Promise<UploadPayload> {
  const { envelope } = params
  const [wrappedForOwner, wrappedForRecovery, recoveryKeyFingerprint] = await Promise.all([
    wrapDekTo(params.ownerPublicKeyPem, envelope.dek),
    wrapDekTo(params.recoveryPublicKeyPem, envelope.dek),
    publicKeyFingerprint(params.recoveryPublicKeyPem),
  ])

  return {
    metadata: {
      file_id: envelope.identity.fileId,
      original_filename: envelope.identity.originalFilename,
      plaintext_size: envelope.identity.plaintextSize,
      mime_type: envelope.identity.mimeType,
      encryption_algorithm: envelope.identity.encryptionAlgorithm,
      envelope_version: envelope.identity.envelopeVersion,
      aad_version: envelope.identity.aadVersion,
      nonce: toBase64(envelope.nonce),
      auth_tag: toBase64(envelope.authTag),
      owner_key_id: params.ownerKeyId,
      key_wrapping_algorithm: KEY_WRAPPING_ALGORITHM,
      wrapped_file_key: toBase64(wrappedForOwner),
      recovery_key_id: params.recoveryKeyId,
      recovery_wrapped_file_key: toBase64(wrappedForRecovery),
    },
    ciphertext: envelope.ciphertext,
    recoveryKeyFingerprint,
  }
}

/**
 * Confirm a DEK opens a file before rewrapping it to someone else.
 *
 * A sharing client cannot verify the recipient's wrapping -- it has no access to their
 * private key -- so the useful check is on its own input. Sharing a DEK that does not open
 * the file creates a grant that silently fails for the recipient.
 */
export async function verifyDekOpensFile(params: {
  identity: FileIdentity
  dek: Uint8Array
  nonce: Uint8Array
  ciphertext: Uint8Array
  authTag: Uint8Array
}): Promise<boolean> {
  try {
    await decryptFile(params)
    return true
  } catch {
    return false
  }
}
