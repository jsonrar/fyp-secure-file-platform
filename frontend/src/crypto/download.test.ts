import { describe, expect, it } from 'vitest'

import {
  PassphraseRejectedError,
  enrolAccountKey,
  unlockAccountPrivateKey,
  unlockAccountPrivateKeyDer,
  type SealedAccountKey,
} from '@/utils/account-crypto'

import { fromBase64, toBase64 } from './encoding'
import { buildUploadPayload, decryptFile, encryptFile, unwrapDek } from './file_envelope'
import { AuthenticationFailure } from './primitives'

const PASSPHRASE = 'a separate encryption passphrase'
const RECOVERY_KEY_ID = '00000000-0000-4000-8000-000000000001'

/** Argon2id at 64 MiB is deliberately slow, so the suite shares one enrolment. */
let enrolment: Awaited<ReturnType<typeof enrolAccountKey>>

async function sharedEnrolment() {
  enrolment ??= await enrolAccountKey(PASSPHRASE)
  return enrolment
}

function sealed(material: Awaited<ReturnType<typeof enrolAccountKey>>['keyMaterial']) {
  return {
    key_id: material.key_id,
    protection: material.protection,
    private_key_bundle: material.private_key_bundle,
  } satisfies SealedAccountKey
}

describe('unlocking the account key', () => {
  it('recovers exactly the private key that was sealed', async () => {
    const { keyMaterial, privateKeyPem } = await sharedEnrolment()

    const der = await unlockAccountPrivateKeyDer(sealed(keyMaterial), PASSPHRASE)

    // `publicKeyPemToDer` refuses a private key by design, so unarmour it here.
    const expected = privateKeyPem
      .replace(/-----(BEGIN|END) PRIVATE KEY-----/g, '')
      .replace(/\s+/g, '')
    expect(toBase64(der)).toBe(expected)
  })

  it('rejects a wrong passphrase at the first envelope', async () => {
    const { keyMaterial } = await sharedEnrolment()

    await expect(
      unlockAccountPrivateKeyDer(sealed(keyMaterial), 'not the passphrase'),
    ).rejects.toBeInstanceOf(PassphraseRejectedError)
  })

  it('uses the KDF cost the profile records, not the current default', async () => {
    // The cost is on the wire precisely so it can be raised later without locking out
    // accounts enrolled under the old one. Deriving with today's constants against
    // yesterday's profile silently produces a different key and reads as a wrong
    // passphrase -- the least debuggable failure available.
    const { keyMaterial } = await sharedEnrolment()
    const wrongCost = {
      ...sealed(keyMaterial),
      protection: { ...keyMaterial.protection, kdf_iterations: keyMaterial.protection.kdf_iterations + 1 },
    }

    await expect(unlockAccountPrivateKeyDer(wrongCost, PASSPHRASE)).rejects.toBeInstanceOf(
      PassphraseRejectedError,
    )
  })

  it('returns a key that can decrypt but cannot be read back out', async () => {
    const { keyMaterial } = await sharedEnrolment()

    const key = await unlockAccountPrivateKey(sealed(keyMaterial), PASSPHRASE)

    expect(key.usages).toEqual(['decrypt'])
    expect(key.extractable).toBe(false)
  })
})

describe('the upload and download halves compose', () => {
  it('round trips a file through wrap, unwrap, and decrypt', async () => {
    // The property the whole product rests on: bytes that went in come back out, using
    // only what the server stores plus the passphrase. Nothing here needs the server.
    const { keyMaterial } = await sharedEnrolment()
    const plaintext = new TextEncoder().encode('chapter one, and everything after it')

    const envelope = await encryptFile({
      plaintext,
      originalFilename: 'dissertation.pdf',
      mimeType: 'application/pdf',
    })
    const payload = await buildUploadPayload({
      envelope,
      ownerKeyId: keyMaterial.key_id,
      ownerPublicKeyPem: keyMaterial.public_key_pem,
      recoveryKeyId: RECOVERY_KEY_ID,
      recoveryPublicKeyPem: keyMaterial.public_key_pem,
    })

    const privateKey = await unlockAccountPrivateKey(sealed(keyMaterial), PASSPHRASE)
    const dek = await unwrapDek(privateKey, fromBase64(payload.metadata.wrapped_file_key))
    const recovered = await decryptFile({
      identity: {
        fileId: payload.metadata.file_id,
        originalFilename: payload.metadata.original_filename,
        plaintextSize: payload.metadata.plaintext_size,
        mimeType: payload.metadata.mime_type,
        envelopeVersion: payload.metadata.envelope_version,
        aadVersion: payload.metadata.aad_version,
        encryptionAlgorithm: payload.metadata.encryption_algorithm,
      },
      dek,
      nonce: fromBase64(payload.metadata.nonce),
      ciphertext: payload.ciphertext,
      authTag: fromBase64(payload.metadata.auth_tag),
    })

    expect(new TextDecoder().decode(recovered)).toBe('chapter one, and everything after it')
  })

  it('refuses a file whose declared filename was changed after upload', async () => {
    // The AAD binds the cleartext columns the server could otherwise rewrite. A server
    // that serves a document under a different name must produce a decryption failure,
    // not a document with a misleading name.
    const { keyMaterial } = await sharedEnrolment()
    const envelope = await encryptFile({
      plaintext: new TextEncoder().encode('payload'),
      originalFilename: 'salary-review.pdf',
      mimeType: 'application/pdf',
    })
    const payload = await buildUploadPayload({
      envelope,
      ownerKeyId: keyMaterial.key_id,
      ownerPublicKeyPem: keyMaterial.public_key_pem,
      recoveryKeyId: RECOVERY_KEY_ID,
      recoveryPublicKeyPem: keyMaterial.public_key_pem,
    })

    const privateKey = await unlockAccountPrivateKey(sealed(keyMaterial), PASSPHRASE)
    const dek = await unwrapDek(privateKey, fromBase64(payload.metadata.wrapped_file_key))

    await expect(
      decryptFile({
        identity: {
          fileId: payload.metadata.file_id,
          originalFilename: 'holiday-photo.jpg',
          plaintextSize: payload.metadata.plaintext_size,
          mimeType: payload.metadata.mime_type,
        },
        dek,
        nonce: fromBase64(payload.metadata.nonce),
        ciphertext: payload.ciphertext,
        authTag: fromBase64(payload.metadata.auth_tag),
      }),
    ).rejects.toBeInstanceOf(AuthenticationFailure)
  })

  it('refuses ciphertext that was altered in storage', async () => {
    const { keyMaterial } = await sharedEnrolment()
    const envelope = await encryptFile({
      plaintext: new TextEncoder().encode('payload that must not be silently mangled'),
      originalFilename: 'notes.txt',
      mimeType: 'text/plain',
    })
    const payload = await buildUploadPayload({
      envelope,
      ownerKeyId: keyMaterial.key_id,
      ownerPublicKeyPem: keyMaterial.public_key_pem,
      recoveryKeyId: RECOVERY_KEY_ID,
      recoveryPublicKeyPem: keyMaterial.public_key_pem,
    })

    const tampered = Uint8Array.from(payload.ciphertext)
    tampered[0] ^= 0xff

    const privateKey = await unlockAccountPrivateKey(sealed(keyMaterial), PASSPHRASE)
    const dek = await unwrapDek(privateKey, fromBase64(payload.metadata.wrapped_file_key))

    await expect(
      decryptFile({
        identity: {
          fileId: payload.metadata.file_id,
          originalFilename: payload.metadata.original_filename,
          plaintextSize: payload.metadata.plaintext_size,
          mimeType: payload.metadata.mime_type,
        },
        dek,
        nonce: fromBase64(payload.metadata.nonce),
        ciphertext: tampered,
        authTag: fromBase64(payload.metadata.auth_tag),
      }),
    ).rejects.toBeInstanceOf(AuthenticationFailure)
  })

  it('cannot unwrap a file key with the wrong account key', async () => {
    const { keyMaterial } = await sharedEnrolment()
    const stranger = await enrolAccountKey('a different account passphrase')

    const envelope = await encryptFile({
      plaintext: new TextEncoder().encode('private'),
      originalFilename: 'private.txt',
      mimeType: 'text/plain',
    })
    const payload = await buildUploadPayload({
      envelope,
      ownerKeyId: keyMaterial.key_id,
      ownerPublicKeyPem: keyMaterial.public_key_pem,
      recoveryKeyId: RECOVERY_KEY_ID,
      recoveryPublicKeyPem: keyMaterial.public_key_pem,
    })

    const strangerKey = await unlockAccountPrivateKey(
      sealed(stranger.keyMaterial),
      'a different account passphrase',
    )

    await expect(
      unwrapDek(strangerKey, fromBase64(payload.metadata.wrapped_file_key)),
    ).rejects.toBeInstanceOf(AuthenticationFailure)
  })
})
