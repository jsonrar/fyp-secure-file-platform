/**
 * Sharing: hand a file to another account without the server ever seeing its key.
 *
 * The mirror of the rewrap half of `download.ts`. `docs/SECURITY_FLOWS.md` describes the
 * flow exactly: the sender unwraps the file's DEK with their own account key, wraps the
 * same DEK to the recipient's public key, and submits only that ciphertext. The server can
 * check the shape of the bytes but never learns the DEK.
 *
 * Until this existed the share dialog posted `{ target_username }` and nothing else, which
 * the strict schema rejected as a 422 -- three required fields missing and one forbidden
 * field present -- while the UI reported "Share request sent". Nothing was ever shared.
 */

import { fileApi } from '@/api/file_api'
import { keyApi } from '@/api/key_api'
import { shareApi } from '@/api/share_api'
import type { FileOut } from '@/api/types'

import { fromBase64, toBase64 } from './encoding'
import {
  FileKeyUnwrapError,
  KeyNotUnlockedError,
  NotUnlockedError,
  isUnlocked,
  unlockedKeyFor,
} from './download'
import { unwrapDek } from './file_envelope'
import { AuthenticationFailure, importRsaOaepPublicKey, rsaOaepWrap } from './primitives'

/** No active account by that name, or it has no key a file could be wrapped to. */
export class RecipientNotFoundError extends Error {
  constructor(username: string) {
    super(`No active account named "${username}" that can receive a shared file`)
    this.name = 'RecipientNotFoundError'
  }
}

/** The recipient named is the sender. The owner already holds the file. */
export class ShareWithSelfError extends Error {
  constructor() {
    super('You already have access to this file')
    this.name = 'ShareWithSelfError'
  }
}

export interface ShareOutcome {
  username: string
  /** False when the grant already existed and was updated rather than created. */
  created: boolean
}

/**
 * Rewrap a file's key to another account and record the grant.
 *
 * Requires the sender's account key to be unlocked, for the same reason downloading does:
 * the DEK is reachable only through it.
 */
export async function shareFileWithUsername(
  fileId: string,
  username: string,
  options: { canDownload?: boolean; canShare?: boolean } = {},
): Promise<ShareOutcome> {
  const name = username.trim()
  if (!name) throw new RecipientNotFoundError(username)
  if (!isUnlocked()) throw new NotUnlockedError()

  let recipient
  try {
    recipient = (await keyApi.activePublicKeyByUsername(name)).data.data
  } catch {
    // A 404 is the ordinary case -- a typo in a colleague's name -- and everything else
    // here is equally "cannot share with them", so it is not worth splitting further.
    throw new RecipientNotFoundError(name)
  }

  const metadata = (await fileApi.getFile(fileId)).data.data as FileOut
  const envelope = metadata.crypto_envelope

  const privateKey = unlockedKeyFor(envelope.key_id)
  if (privateKey === undefined) {
    // Ordinary after a key rotation: the file is wrapped to a key this session has not
    // opened. Naming it lets the caller offer to unlock that key.
    throw new KeyNotUnlockedError(envelope.key_id)
  }

  let dek: Uint8Array
  try {
    dek = await unwrapDek(privateKey, fromBase64(envelope.wrapped_file_key))
  } catch (error) {
    if (error instanceof AuthenticationFailure) throw new FileKeyUnwrapError()
    throw error
  }

  // RSA-OAEP authenticates, and unwrapDek checks the length, so a DEK that reaches here is
  // the one that was sealed. The sender cannot verify the outgoing wrapping -- that needs
  // the recipient's private key -- which is why the server also checks its shape.
  const recipientKey = await importRsaOaepPublicKey(recipient.public_key_pem)
  const wrappedForRecipient = await rsaOaepWrap(recipientKey, dek)

  const response = await shareApi.shareFile(fileId, {
    target_user_id: recipient.user_id,
    target_key_id: recipient.key_id,
    wrapped_file_key: toBase64(wrappedForRecipient),
    can_download: options.canDownload ?? true,
    can_share: options.canShare ?? false,
  })

  return { username: name, created: response.data.data?.created ?? true }
}
