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
 * The associated data for both envelopes is rebuildable from stored non-secret
 * metadata, so a later unlock can reconstruct it without extra server state.
 */
import { argon2id } from 'hash-wasm'

/** Must match the backend USER_RSA_KEY_SIZE setting. */
export const RSA_KEY_SIZE_BITS = 3072

/** Backend KeyProtectionProfileIn requires at least 65536 KiB. */
const ARGON2_MEMORY_KIB = 65536
const ARGON2_ITERATIONS = 3
const ARGON2_PARALLELISM = 1
const ARGON2_VERSION = 19

const KDF_SALT_BYTES = 16
const AMK_BYTES = 32
const GCM_NONCE_BYTES = 12
const GCM_TAG_BYTES = 16
const DERIVED_KEY_BYTES = 32
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

export class UnsupportedCryptoError extends Error {
  constructor() {
    super(
      'This browser does not expose Web Crypto. Use a current browser over HTTPS or localhost.',
    )
    this.name = 'UnsupportedCryptoError'
  }
}

function subtle(): SubtleCrypto {
  if (typeof globalThis.crypto?.subtle === 'undefined') {
    throw new UnsupportedCryptoError()
  }
  return globalThis.crypto.subtle
}

function randomBytes(length: number): Uint8Array {
  const buffer = new Uint8Array(length)
  globalThis.crypto.getRandomValues(buffer)
  return buffer
}

function toBase64(bytes: Uint8Array): string {
  let binary = ''
  for (const byte of bytes) {
    binary += String.fromCharCode(byte)
  }
  return btoa(binary)
}

function toHex(bytes: Uint8Array): string {
  return Array.from(bytes, (byte) => byte.toString(16).padStart(2, '0')).join('')
}

function utf8(value: string): Uint8Array {
  return new TextEncoder().encode(value)
}

function bytesEqual(left: Uint8Array, right: Uint8Array): boolean {
  if (left.length !== right.length) {
    return false
  }
  return left.every((byte, index) => byte === right[index])
}

function toPem(label: string, der: ArrayBuffer): string {
  const base64 = toBase64(new Uint8Array(der))
  const lines = base64.match(/.{1,64}/g) ?? []
  return `-----BEGIN ${label}-----\n${lines.join('\n')}\n-----END ${label}-----\n`
}

/** AES-GCM output is ciphertext||tag; the API stores the two parts separately. */
function splitCiphertextAndTag(sealed: ArrayBuffer): {
  ciphertext: Uint8Array
  tag: Uint8Array
} {
  const bytes = new Uint8Array(sealed)
  return {
    ciphertext: bytes.slice(0, bytes.length - GCM_TAG_BYTES),
    tag: bytes.slice(bytes.length - GCM_TAG_BYTES),
  }
}

function joinCiphertextAndTag(ciphertext: Uint8Array, tag: Uint8Array): Uint8Array {
  const joined = new Uint8Array(ciphertext.length + tag.length)
  joined.set(ciphertext, 0)
  joined.set(tag, ciphertext.length)
  return joined
}

function amkWrapAad(profileId: string): Uint8Array {
  return utf8(`secureview:amk-wrap:v1:${profileId}`)
}

function privateKeyAad(bundleId: string, keyId: string): Uint8Array {
  return utf8(`secureview:private-key:v1:${bundleId}:${keyId}`)
}

async function deriveKek(passphrase: string, salt: Uint8Array): Promise<Uint8Array> {
  const derived = await argon2id({
    password: passphrase,
    salt,
    parallelism: ARGON2_PARALLELISM,
    iterations: ARGON2_ITERATIONS,
    memorySize: ARGON2_MEMORY_KIB,
    hashLength: DERIVED_KEY_BYTES,
    outputType: 'binary',
  })
  return derived
}

async function importAesKey(raw: Uint8Array, usages: KeyUsage[]): Promise<CryptoKey> {
  return subtle().importKey('raw', raw as BufferSource, { name: 'AES-GCM' }, false, usages)
}

async function derivePrivateKeyEncryptionKey(
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
    DERIVED_KEY_BYTES * 8,
  )
  return new Uint8Array(bits)
}

async function sha256Hex(bytes: Uint8Array): Promise<string> {
  const digest = await subtle().digest('SHA-256', bytes as BufferSource)
  return toHex(new Uint8Array(digest))
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

  const keyId = globalThis.crypto.randomUUID()
  const profileId = globalThis.crypto.randomUUID()
  const bundleId = globalThis.crypto.randomUUID()

  // 1. Wrap a fresh random AMK under an Argon2id-derived KEK.
  const amk = randomBytes(AMK_BYTES)
  const kdfSalt = randomBytes(KDF_SALT_BYTES)
  const kek = await deriveKek(passphrase, kdfSalt)
  const amkNonce = randomBytes(GCM_NONCE_BYTES)
  const amkAad = amkWrapAad(profileId)
  const sealedAmk = await crypto.encrypt(
    { name: 'AES-GCM', iv: amkNonce as BufferSource, additionalData: amkAad as BufferSource },
    await importAesKey(kek, ['encrypt']),
    amk as BufferSource,
  )
  const wrappedAmk = splitCiphertextAndTag(sealedAmk)

  // 2. Encrypt the PKCS#8 private key under an AMK/HKDF-derived key.
  const hkdfSalt = randomBytes(HKDF_SALT_BYTES)
  const privateKeyAadBytes = privateKeyAad(bundleId, keyId)
  const privateKeyKey = await derivePrivateKeyEncryptionKey(amk, hkdfSalt, privateKeyAadBytes)
  const privateKeyNonce = randomBytes(GCM_NONCE_BYTES)
  const sealedPrivateKey = await crypto.encrypt(
    {
      name: 'AES-GCM',
      iv: privateKeyNonce as BufferSource,
      additionalData: privateKeyAadBytes as BufferSource,
    },
    await importAesKey(privateKeyKey, ['encrypt']),
    privateKeyDer as BufferSource,
  )
  const sealedBundle = splitCiphertextAndTag(sealedPrivateKey)

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
      derived_key_length: DERIVED_KEY_BYTES,
      amk_wrapping_algorithm: 'AES-256-GCM',
      wrapped_amk: toBase64(wrappedAmk.ciphertext),
      amk_nonce: toBase64(amkNonce),
      amk_auth_tag: toBase64(wrappedAmk.tag),
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
      auth_tag: toBase64(sealedBundle.tag),
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
async function assertEnvelopesUnlock(
  keyMaterial: ClientKeyMaterial,
  passphrase: string,
  expectedPrivateKeyDer: Uint8Array,
): Promise<void> {
  const crypto = subtle()
  const { protection, private_key_bundle: bundle } = keyMaterial

  const kdfSalt = fromBase64(protection.kdf_salt)
  const kek = await deriveKek(passphrase, kdfSalt)
  const recoveredAmk = new Uint8Array(
    await crypto.decrypt(
      {
        name: 'AES-GCM',
        iv: fromBase64(protection.amk_nonce) as BufferSource,
        additionalData: amkWrapAad(protection.profile_id) as BufferSource,
      },
      await importAesKey(kek, ['decrypt']),
      joinCiphertextAndTag(
        fromBase64(protection.wrapped_amk),
        fromBase64(protection.amk_auth_tag),
      ) as BufferSource,
    ),
  )

  const aad = privateKeyAad(bundle.bundle_id, keyMaterial.key_id)
  const privateKeyKey = await derivePrivateKeyEncryptionKey(
    recoveredAmk,
    fromBase64(bundle.derivation_salt),
    aad,
  )
  const recoveredDer = new Uint8Array(
    await crypto.decrypt(
      {
        name: 'AES-GCM',
        iv: fromBase64(bundle.nonce) as BufferSource,
        additionalData: aad as BufferSource,
      },
      await importAesKey(privateKeyKey, ['decrypt']),
      joinCiphertextAndTag(
        fromBase64(bundle.encrypted_private_key),
        fromBase64(bundle.auth_tag),
      ) as BufferSource,
    ),
  )

  if (!bytesEqual(recoveredDer, expectedPrivateKeyDer)) {
    throw new Error('Account key self-test failed; registration was not attempted')
  }
}

export function fromBase64(value: string): Uint8Array {
  const binary = atob(value)
  const bytes = new Uint8Array(binary.length)
  for (let index = 0; index < binary.length; index += 1) {
    bytes[index] = binary.charCodeAt(index)
  }
  return bytes
}
