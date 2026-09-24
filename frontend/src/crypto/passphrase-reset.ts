/**
 * Reset a forgotten encryption passphrase with the private key file saved at registration.
 *
 * The passphrase never protected the files directly: it wraps the account master key (AMK),
 * and the AMK seals a copy of the private key. Forgetting it loses the AMK -- nothing on the
 * server or in this code can recover that -- but the private key file is the thing the AMK
 * was protecting all along. So the reset seals that same key again, under a fresh AMK and a
 * new passphrase. The key pair and its id do not change, so every file wrapping and every
 * share grant keeps working, and no file is re-encrypted.
 *
 * The server checks an RSA-PSS signature made with this key before accepting the new
 * envelopes. It cannot check that they open -- it never holds the passphrase, the AMK, or
 * the private key -- so the signature is what stops a stolen session from overwriting them.
 */

import { keyApi, type ResetKeyProtectionBody } from '@/api/key_api'
import { bytesEqual, fromBase64, toBase64 } from './encoding'
import { assertKeyPairMatches } from './download'
import {
  importRsaOaepPrivateKey,
  importRsaPssPrivateKey,
  privateKeyPemToDer,
  rsaPssSign,
} from './primitives'
import { sealAccountKey, unlockAccountPrivateKeyDer } from '@/utils/account-crypto'
import { PASSPHRASE_MIN_LENGTH, passphraseLength } from '@/utils/password-policy'

/** The new passphrase is too short to protect a key that opens every file. */
export class PassphraseTooShortError extends Error {
  constructor() {
    super(`The new encryption passphrase must be at least ${PASSPHRASE_MIN_LENGTH} characters`)
    this.name = 'PassphraseTooShortError'
  }
}

/**
 * The server accepted the reset, but the envelopes it now serves do not open.
 *
 * Should not happen -- the same envelopes opened locally a moment earlier -- but the account
 * is not lost if it does: the key pair is unchanged, so the private key file still opens
 * every file, and a second reset can be attempted with it.
 */
export class ResetVerificationError extends Error {
  constructor() {
    super(
      'The new passphrase was saved but could not be verified. Keep your private key file; it still opens every file.',
    )
    this.name = 'ResetVerificationError'
  }
}

export interface PassphraseResetOutcome {
  keyId: string
  profileRevision: number
  bundleRevision: number
}

/**
 * Seal the account private key under a new passphrase and a fresh AMK, then register both.
 *
 * Every check that can fail without touching the account runs first: the file must parse,
 * be this account's key, and produce envelopes that reopen to the same bytes. Only then does
 * anything leave the browser, and only ciphertext does. After the server accepts, the stored
 * envelopes are fetched back and opened once more, because what matters is what the next
 * unlock will read, not what was sent.
 */
export async function resetPassphraseWithPrivateKeyPem(
  pem: string,
  newPassphrase: string,
): Promise<PassphraseResetOutcome> {
  if (passphraseLength(newPassphrase) < PASSPHRASE_MIN_LENGTH) {
    throw new PassphraseTooShortError()
  }

  const current = (await keyApi.myBundle()).data.data
  const privateKeyDer = privateKeyPemToDer(pem)

  // Raises PrivateKeyMismatchError for a key from another account, before anything is sealed.
  await assertKeyPairMatches(await importRsaOaepPrivateKey(privateKeyDer), current.key.public_key_pem)

  // Same ids as the envelopes being replaced: both AADs are built from them, and the rows are
  // updated in place rather than recreated.
  const sealed = await sealAccountKey({
    privateKeyDer,
    passphrase: newPassphrase,
    keyId: current.key.key_id,
    profileId: current.protection.profile_id,
    bundleId: current.private_key_bundle.bundle_id,
  })

  const reopened = await unlockAccountPrivateKeyDer(
    { key_id: current.key.key_id, ...sealed },
    newPassphrase,
  )
  if (!bytesEqual(reopened, privateKeyDer)) {
    throw new ResetVerificationError()
  }

  const body: ResetKeyProtectionBody = {
    authorizing_key_id: current.key.key_id,
    expected_profile_revision: current.protection.revision,
    expected_bundle_revision: current.private_key_bundle.revision,
    protection: sealed.protection,
    private_key_bundle: sealed.private_key_bundle,
  }

  const challenge = (await keyApi.resetProtectionSigningPayload(body)).data.data
  const signature = await rsaPssSign(
    await importRsaPssPrivateKey(privateKeyDer),
    fromBase64(challenge.authorization_payload),
  )
  const result = (
    await keyApi.resetProtection({ ...body, authorization_signature: toBase64(signature) })
  ).data.data

  const stored = (await keyApi.myBundle()).data.data
  let fromServer: Uint8Array
  try {
    fromServer = await unlockAccountPrivateKeyDer(
      {
        key_id: stored.key.key_id,
        protection: stored.protection,
        private_key_bundle: stored.private_key_bundle,
      },
      newPassphrase,
    )
  } catch {
    throw new ResetVerificationError()
  }
  if (!bytesEqual(fromServer, privateKeyDer)) {
    throw new ResetVerificationError()
  }

  return {
    keyId: stored.key.key_id,
    profileRevision: result.profile_revision,
    bundleRevision: result.bundle_revision,
  }
}
