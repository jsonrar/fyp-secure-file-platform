/**
 * Encrypted download: turn what `POST /files/{id}/download` returns back into the file.
 *
 * The mirror of `upload.ts`. The server hands over ciphertext and an envelope describing
 * it; everything that makes those bytes readable happens here, in the page, under a key
 * the server has never held.
 *
 * Until this existed a file could be uploaded and never retrieved: the download button
 * fetched the ciphertext and discarded it, so the plaintext was gone the moment the
 * uploading tab closed.
 */

import { fileApi } from '@/api/file_api'
import { keyApi } from '@/api/key_api'
import type { FileOut } from '@/api/types'
import {
  type SealedAccountKey,
  unlockAccountPrivateKey,
} from '@/utils/account-crypto'

import { fromBase64 } from './encoding'
import { decryptFile, unwrapDek } from './file_envelope'
import { AuthenticationFailure } from './primitives'

/**
 * Account keys, opened once and reused, keyed by the id they were opened for.
 *
 * Argon2id at the enrolled cost takes a noticeable moment by design, so asking for the
 * passphrase on every file would make downloading several files unpleasant enough that
 * people would look for a way around it. Keys are non-extractable and live only in this
 * module's closure: nothing is written to storage, and a reload discards them.
 *
 * Keyed by id rather than held as a single key because a file stays wrapped to whichever
 * key was active when it was uploaded. After a rotation an account can legitimately need
 * an older key to read an older file, and `GET /keys/me/{key_id}` still serves it.
 */
const unlockedKeys = new Map<string, CryptoKey>()

export function forgetUnlockedKeys(): void {
  unlockedKeys.clear()
}

export function isUnlocked(): boolean {
  return unlockedKeys.size > 0
}

async function openBundle(
  bundle: { key: { key_id: string }; protection: unknown; private_key_bundle: unknown },
  passphrase: string,
): Promise<string> {
  const sealed = {
    key_id: bundle.key.key_id,
    protection: bundle.protection,
    private_key_bundle: bundle.private_key_bundle,
  } as SealedAccountKey
  unlockedKeys.set(sealed.key_id, await unlockAccountPrivateKey(sealed, passphrase))
  return sealed.key_id
}

/** Open the account's active key. Throws `PassphraseRejectedError` if the passphrase is wrong. */
export async function unlockWithPassphrase(passphrase: string): Promise<void> {
  const response = await keyApi.myBundle()
  await openBundle(response.data.data, passphrase)
}

/** Open a superseded key, for a file uploaded before the account rotated. */
export async function unlockOwnedKey(keyId: string, passphrase: string): Promise<void> {
  const response = await keyApi.ownedBundle(keyId)
  await openBundle(response.data.data, passphrase)
}

/**
 * The file is wrapped to a key this session has not opened.
 *
 * Carries the id so the caller can offer to unlock that key rather than reporting a dead
 * end -- the situation is ordinary after a key rotation, not an error in the file.
 */
export class KeyNotUnlockedError extends Error {
  readonly keyId: string

  constructor(keyId: string) {
    super(`This file is wrapped to account key ${keyId}, which is not unlocked`)
    this.name = 'KeyNotUnlockedError'
    this.keyId = keyId
  }
}

export class NotUnlockedError extends Error {
  constructor() {
    super('The account key is locked; a passphrase is required first')
    this.name = 'NotUnlockedError'
  }
}

export interface DecryptedFile {
  filename: string
  mimeType: string
  bytes: Uint8Array
}

/**
 * Download one file and decrypt it.
 *
 * The envelope is fetched separately from the ciphertext because the two answer different
 * questions: `GET /files/{id}` carries the caller's own wrapped file key, the nonce and the
 * tag, while the download route streams bytes the server has already verified against the
 * digest recorded at upload.
 */
export async function downloadAndDecrypt(fileId: string): Promise<DecryptedFile> {
  if (unlockedKeys.size === 0) {
    throw new NotUnlockedError()
  }

  const metadata = (await fileApi.getFile(fileId)).data.data as FileOut
  const envelope = metadata.crypto_envelope

  // The envelope carries the key id this caller's wrapping was made for. Naming a missing
  // key beats an unexplained authentication failure three steps further in.
  const privateKey = unlockedKeys.get(envelope.key_id)
  if (privateKey === undefined) {
    throw new KeyNotUnlockedError(envelope.key_id)
  }

  const response = await fileApi.download(fileId)
  const ciphertext = new Uint8Array(response.data as ArrayBuffer)

  const dek = await unwrapDek(privateKey, fromBase64(envelope.wrapped_file_key))
  const plaintext = await decryptFile({
    identity: {
      fileId: metadata.file_id,
      originalFilename: metadata.original_filename,
      plaintextSize: metadata.plaintext_size,
      mimeType: metadata.mime_type ?? 'application/octet-stream',
      envelopeVersion: envelope.envelope_version,
      aadVersion: envelope.aad_version,
      encryptionAlgorithm: envelope.encryption_algorithm,
    },
    dek,
    nonce: fromBase64(envelope.nonce),
    ciphertext,
    authTag: fromBase64(envelope.auth_tag),
  })

  // The AAD binds plaintext_size, so a mismatch here should be unreachable. Checking costs
  // nothing and turns a corrupted save into a refusal the user can act on.
  if (plaintext.length !== metadata.plaintext_size) {
    throw new AuthenticationFailure(
      `Decrypted ${plaintext.length} bytes but the envelope declares ${metadata.plaintext_size}`,
    )
  }

  return {
    filename: metadata.original_filename,
    mimeType: metadata.mime_type ?? 'application/octet-stream',
    bytes: plaintext,
  }
}

/** Hand the decrypted bytes to the browser as a download. */
export function saveDecryptedFile(file: DecryptedFile): void {
  const blob = new Blob([file.bytes as BlobPart], { type: file.mimeType })
  const url = URL.createObjectURL(blob)
  try {
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = file.filename
    document.body.appendChild(anchor)
    anchor.click()
    anchor.remove()
  } finally {
    // Revoking immediately can race the save on some browsers; one tick is enough for the
    // click to have been dispatched, and leaking the object URL keeps the plaintext alive
    // in memory for the lifetime of the document.
    setTimeout(() => URL.revokeObjectURL(url), 0)
  }
}

