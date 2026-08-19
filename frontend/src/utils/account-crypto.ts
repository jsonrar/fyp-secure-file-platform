/**
 * Client-side account key enrolment.
 *
 * The encryption passphrase never leaves this module. The browser generates the
 * RSA key pair and a random account master key (AMK), wraps the AMK under an
 * Argon2id-derived key-encryption key (KEK), and encrypts the PKCS#8 private key
 * under an AMK/HKDF-derived key. Only the public key and the two sealed
 * envelopes are uploaded, which is the client-custody boundary described in
 * docs/SECURITY_FLOWS.md.
 *
 * Low-level operations come from `@/crypto/primitives` and `@/crypto/encoding`
 * so this module and the file-envelope code share one vetted implementation.
 * Only the pieces those modules do not provide live here: RSA key-pair
 * generation, the Argon2id KEK, and the HKDF-SHA256 private-key key.
 *
 * The associated data for both envelopes is rebuildable from stored non-secret
 * metadata, so a later unlock can reconstruct it without extra server state.
 */
import { argon2id } from 'hash-wasm'

import { bytesEqual, fromBase64, toBase64, utf8Bytes } from '@/crypto/encoding'
import {
  AES_GCM_NONCE_BYTES,
  AES_KEY_BYTES,
  aesGcmDecryptDetached,
  aesGcmEncryptDetached,
  importAesGcmKey,
  randomBytes,
  randomUuid,
  sha256Hex,
} from '@/crypto/primitives'

/** Must match the backend USER_RSA_KEY_SIZE setting. */
export const RSA_KEY_SIZE_BITS = 3072

/** Backend KeyProtectionProfileIn requires at least 65536 KiB. */
export const ARGON2_MEMORY_KIB = 65536
export const ARGON2_ITERATIONS = 3
export const ARGON2_PARALLELISM = 1
const ARGON2_VERSION = 19

const KDF_SALT_BYTES = 16
const HKDF_SALT_BYTES = 32

export interface KeyProtectionProfilePayload {
  profile_id: string
  format_version: 1
  kdf_algorithm: 'ARGON2ID'
  kdf_version: 19
  kdf_salt: string
  kdf_memory_kib: number
  kdf_iterations: number
  kdf_parallelism: number
  derived_key_length: 32
  amk_wrapping_algorithm: 'AES-256-GCM'
  wrapped_amk: string
  amk_nonce: string
  amk_auth_tag: string
  aad_version: 1
}

export interface EncryptedPrivateKeyBundlePayload {
  bundle_id: string
  format_version: 1
  private_key_format: 'PKCS8-DER'
  derivation_algorithm: 'HKDF-SHA256'
  derivation_salt: string
  encryption_algorithm: 'AES-256-GCM'
  encrypted_private_key: string
  nonce: string
  auth_tag: string
  aad_version: 1
  ciphertext_sha256: string
}

export interface ClientKeyMaterial {
  key_id: string
  public_key_pem: string
  algorithm: 'RSA-OAEP-SHA256'
  key_size_bits: number
  protection: KeyProtectionProfilePayload
  private_key_bundle: EncryptedPrivateKeyBundlePayload
}

export interface EnrolmentResult {
  /** Upload this. It contains no passphrase, AMK, or plaintext private key. */
  keyMaterial: ClientKeyMaterial
  /**
   * Shown to the user once so they can keep an offline copy. This is never
   * transmitted and is dropped as soon as the page navigates away.
   */
  privateKeyPem: string
}

export class AccountKeySelfTestError extends Error {
  constructor() {
    super('Account key self-test failed; registration was not attempted')
    this.name = 'AccountKeySelfTestError'
  }
}

function subtle(): SubtleCrypto {
  const api = globalThis.crypto?.subtle
  if (!api) {
    throw new Error('WebCrypto is unavailable; a secure context (HTTPS or localhost) is required')
  }
  return api
}

function toPem(label: string, der: ArrayBuffer): string {
  const base64 = toBase64(new Uint8Array(der))
  const lines = base64.match(/.{1,64}/g) ?? []
  return `-----BEGIN ${label}-----\n${lines.join('\n')}\n-----END ${label}-----\n`
}

/** AAD for the wrapped AMK, rebuildable from the stored protection profile. */
export function amkWrapAad(profileId: string): Uint8Array {
  return utf8Bytes(`secureview:amk-wrap:v1:${profileId}`)
}

/** AAD for the private-key bundle, rebuildable from the stored bundle and key. */
export function privateKeyAad(bundleId: string, keyId: string): Uint8Array {
  return utf8Bytes(`secureview:private-key:v1:${bundleId}:${keyId}`)
}

/** Argon2id KEK derivation. `hash-wasm` supplies what WebCrypto does not. */
export async function deriveKek(passphrase: string, salt: Uint8Array): Promise<Uint8Array> {
  return argon2id({
    password: passphrase,
    salt,
    parallelism: ARGON2_PARALLELISM,
    iterations: ARGON2_ITERATIONS,
    memorySize: ARGON2_MEMORY_KIB,
    hashLength: AES_KEY_BYTES,
    outputType: 'binary',
  })
}

/** HKDF-SHA256 private-key encryption key, bound to the bundle AAD as `info`. */
export async function derivePrivateKeyEncryptionKey(
  amk: Uint8Array,
  salt: Uint8Array,
  info: Uint8Array,
): Promise<Uint8Array> {
  const hkdfKey = await subtle().importKey('raw', amk as BufferSource, 'HKDF', false, [
    'deriveBits',
  ])
  const bits = await subtle().deriveBits(
    { name: 'HKDF', hash: 'SHA-256', salt: salt as BufferSource, info: info as BufferSource },
    hkdfKey,
    AES_KEY_BYTES * 8,
  )
  return new Uint8Array(bits)
}

/**
 * Generate an account key pair and seal it under the passphrase.
 *
 * Throws if the self-test cannot recover the private key, so a broken envelope
 * is never registered against a new account.
 */
export async function enrolAccountKey(passphrase: string): Promise<EnrolmentResult> {
  const crypto = subtle()

  const keyPair = (await crypto.generateKey(
    {
      name: 'RSA-OAEP',
      modulusLength: RSA_KEY_SIZE_BITS,
      publicExponent: new Uint8Array([1, 0, 1]),
      hash: 'SHA-256',
    },
    true,
    ['encrypt', 'decrypt'],
  )) as CryptoKeyPair

  const spki = await crypto.exportKey('spki', keyPair.publicKey)
  const pkcs8 = await crypto.exportKey('pkcs8', keyPair.privateKey)
  const publicKeyPem = toPem('PUBLIC KEY', spki)
  const privateKeyPem = toPem('PRIVATE KEY', pkcs8)
  const privateKeyDer = new Uint8Array(pkcs8)

  const keyId = randomUuid()
  const profileId = randomUuid()
  const bundleId = randomUuid()

  // 1. Wrap a fresh random AMK under an Argon2id-derived KEK.
  const amk = randomBytes(AES_KEY_BYTES)
  const kdfSalt = randomBytes(KDF_SALT_BYTES)
  const kek = await deriveKek(passphrase, kdfSalt)
  const amkNonce = randomBytes(AES_GCM_NONCE_BYTES)
  const wrappedAmk = await aesGcmEncryptDetached({
    key: await importAesGcmKey(kek),
    nonce: amkNonce,
    plaintext: amk,
    aad: amkWrapAad(profileId),
  })

  // 2. Encrypt the PKCS#8 private key under an AMK/HKDF-derived key.
  const hkdfSalt = randomBytes(HKDF_SALT_BYTES)
  const bundleAad = privateKeyAad(bundleId, keyId)
  const privateKeyKey = await derivePrivateKeyEncryptionKey(amk, hkdfSalt, bundleAad)
  const privateKeyNonce = randomBytes(AES_GCM_NONCE_BYTES)
  const sealedBundle = await aesGcmEncryptDetached({
    key: await importAesGcmKey(privateKeyKey),
    nonce: privateKeyNonce,
    plaintext: privateKeyDer,
    aad: bundleAad,
  })

  const keyMaterial: ClientKeyMaterial = {
    key_id: keyId,
    public_key_pem: publicKeyPem,
    algorithm: 'RSA-OAEP-SHA256',
    key_size_bits: RSA_KEY_SIZE_BITS,
    protection: {
      profile_id: profileId,
      format_version: 1,
      kdf_algorithm: 'ARGON2ID',
      kdf_version: ARGON2_VERSION,
      kdf_salt: toBase64(kdfSalt),
      kdf_memory_kib: ARGON2_MEMORY_KIB,
      kdf_iterations: ARGON2_ITERATIONS,
      kdf_parallelism: ARGON2_PARALLELISM,
      derived_key_length: AES_KEY_BYTES,
      amk_wrapping_algorithm: 'AES-256-GCM',
      wrapped_amk: toBase64(wrappedAmk.ciphertext),
      amk_nonce: toBase64(amkNonce),
      amk_auth_tag: toBase64(wrappedAmk.authTag),
      aad_version: 1,
    },
    private_key_bundle: {
      bundle_id: bundleId,
      format_version: 1,
      private_key_format: 'PKCS8-DER',
      derivation_algorithm: 'HKDF-SHA256',
      derivation_salt: toBase64(hkdfSalt),
      encryption_algorithm: 'AES-256-GCM',
      encrypted_private_key: toBase64(sealedBundle.ciphertext),
      nonce: toBase64(privateKeyNonce),
      auth_tag: toBase64(sealedBundle.authTag),
      aad_version: 1,
      ciphertext_sha256: await sha256Hex(sealedBundle.ciphertext),
    },
  }

  await assertEnvelopesUnlock(keyMaterial, passphrase, privateKeyDer)

  return { keyMaterial, privateKeyPem }
}

/**
 * Re-derive both envelopes from the passphrase and confirm they return the same
 * private key. Registering an envelope that cannot be reopened would lock the
 * account out of every file it later encrypts.
 */
export async function assertEnvelopesUnlock(
  keyMaterial: ClientKeyMaterial,
  passphrase: string,
  expectedPrivateKeyDer: Uint8Array,
): Promise<void> {
  const { protection, private_key_bundle: bundle } = keyMaterial

  const kek = await deriveKek(passphrase, fromBase64(protection.kdf_salt))
  const recoveredAmk = await aesGcmDecryptDetached({
    key: await importAesGcmKey(kek),
    nonce: fromBase64(protection.amk_nonce),
    ciphertext: fromBase64(protection.wrapped_amk),
    authTag: fromBase64(protection.amk_auth_tag),
    aad: amkWrapAad(protection.profile_id),
  })

  const bundleAad = privateKeyAad(bundle.bundle_id, keyMaterial.key_id)
  const privateKeyKey = await derivePrivateKeyEncryptionKey(
    recoveredAmk,
    fromBase64(bundle.derivation_salt),
    bundleAad,
  )
  const recoveredDer = await aesGcmDecryptDetached({
    key: await importAesGcmKey(privateKeyKey),
    nonce: fromBase64(bundle.nonce),
    ciphertext: fromBase64(bundle.encrypted_private_key),
    authTag: fromBase64(bundle.auth_tag),
    aad: bundleAad,
  })

  if (!bytesEqual(recoveredDer, expectedPrivateKeyDer)) {
    throw new AccountKeySelfTestError()
  }
}
