/**
 * WebCrypto wrappers for the algorithm suite.
 *
 * Every function here is a thin, testable primitive: it takes bytes and returns bytes.
 * Envelope construction, AAD layout, and business rules live in the modules above this one.
 */

import { bytesToHex, fromBase64 } from './encoding'

export const AES_KEY_BYTES = 32
export const AES_GCM_NONCE_BYTES = 12
export const AES_GCM_TAG_BYTES = 16
export const AES_GCM_TAG_BITS = AES_GCM_TAG_BYTES * 8

/** RSA-PSS salt length in **bytes**, matching the digest length. WebCrypto counts bytes. */
export const RSA_PSS_SALT_BYTES = 32

/**
 * An AEAD tag did not verify.
 *
 * Raised instead of the raw `OperationError` so callers can distinguish an authentication
 * failure from a programming error. An authentication failure alone does not identify its
 * cause: a wrong key, a substituted envelope, and corrupt ciphertext are indistinguishable
 * to AES-GCM, so callers must run their structural checks before attributing blame.
 */
export class AuthenticationFailure extends Error {
  constructor(message = 'AES-GCM authentication failed') {
    super(message)
    this.name = 'AuthenticationFailure'
  }
}

function subtle(): SubtleCrypto {
  const api = globalThis.crypto?.subtle
  if (!api) {
    throw new Error('WebCrypto is unavailable; a secure context (HTTPS or localhost) is required')
  }
  return api
}

/** Cryptographically secure random bytes. Never `Math.random`. */
export function randomBytes(length: number): Uint8Array {
  const out = new Uint8Array(length)
  globalThis.crypto.getRandomValues(out)
  return out
}

/** A random RFC 4122 version 4 UUID from the platform CSPRNG. */
export function randomUuid(): string {
  return globalThis.crypto.randomUUID()
}

/** SHA-256 over the given bytes. */
export async function sha256(data: Uint8Array): Promise<Uint8Array> {
  const digest = await subtle().digest('SHA-256', data as BufferSource)
  return new Uint8Array(digest)
}

/** SHA-256 as a 64-character lowercase hex string. */
export async function sha256Hex(data: Uint8Array): Promise<string> {
  return bytesToHex(await sha256(data))
}

/**
 * Import raw AES-256 key bytes.
 *
 * Non-extractable by default: the handle cannot be read back out by any script that later
 * runs in the page. This does not protect the raw bytes the caller already holds — a data
 * encryption key must stay readable to be wrapped with RSA-OAEP — but it does stop the
 * imported key from becoming a second copy.
 */
export async function importAesGcmKey(raw: Uint8Array, extractable = false): Promise<CryptoKey> {
  if (raw.length !== AES_KEY_BYTES) {
    throw new RangeError(`AES-256 key must be ${AES_KEY_BYTES} bytes, received ${raw.length}`)
  }
  return subtle().importKey('raw', raw as BufferSource, 'AES-GCM', extractable, [
    'encrypt',
    'decrypt',
  ])
}

export interface AesGcmCiphertext {
  ciphertext: Uint8Array
  authTag: Uint8Array
}

/**
 * AES-256-GCM encryption with a **detached** authentication tag.
 *
 * `crypto.subtle.encrypt` returns `ciphertext ‖ tag` as one buffer, but the API stores the
 * tag in its own column and the stored ciphertext excludes it. The split is enforced
 * numerically on the server: `wrapped_amk` must decode to exactly 32 bytes, and an uploaded
 * file's ciphertext length must equal its declared `plaintext_size`. Returning a joined
 * buffer here would be rejected at every one of those checks.
 */
export async function aesGcmEncryptDetached(params: {
  key: CryptoKey
  nonce: Uint8Array
  plaintext: Uint8Array
  aad: Uint8Array
}): Promise<AesGcmCiphertext> {
  const { key, nonce, plaintext, aad } = params
  if (nonce.length !== AES_GCM_NONCE_BYTES) {
    throw new RangeError(`AES-GCM nonce must be ${AES_GCM_NONCE_BYTES} bytes`)
  }
  const joined = new Uint8Array(
    await subtle().encrypt(
      {
        name: 'AES-GCM',
        iv: nonce as BufferSource,
        additionalData: aad as BufferSource,
        tagLength: AES_GCM_TAG_BITS,
      },
      key,
      plaintext as BufferSource,
    ),
  )
  return {
    ciphertext: joined.slice(0, joined.length - AES_GCM_TAG_BYTES),
    authTag: joined.slice(joined.length - AES_GCM_TAG_BYTES),
  }
}

/** AES-256-GCM decryption, rejoining the detached tag before verification. */
export async function aesGcmDecryptDetached(params: {
  key: CryptoKey
  nonce: Uint8Array
  ciphertext: Uint8Array
  authTag: Uint8Array
  aad: Uint8Array
}): Promise<Uint8Array> {
  const { key, nonce, ciphertext, authTag, aad } = params
  if (nonce.length !== AES_GCM_NONCE_BYTES) {
    throw new RangeError(`AES-GCM nonce must be ${AES_GCM_NONCE_BYTES} bytes`)
  }
  if (authTag.length !== AES_GCM_TAG_BYTES) {
    throw new RangeError(`AES-GCM tag must be ${AES_GCM_TAG_BYTES} bytes`)
  }
  const joined = new Uint8Array(ciphertext.length + authTag.length)
  joined.set(ciphertext, 0)
  joined.set(authTag, ciphertext.length)
  try {
    const plaintext = await subtle().decrypt(
      {
        name: 'AES-GCM',
        iv: nonce as BufferSource,
        additionalData: aad as BufferSource,
        tagLength: AES_GCM_TAG_BITS,
      },
      key,
      joined as BufferSource,
    )
    return new Uint8Array(plaintext)
  } catch {
    throw new AuthenticationFailure()
  }
}

const PEM_PUBLIC_KEY = /-----BEGIN PUBLIC KEY-----([\s\S]+?)-----END PUBLIC KEY-----/

/** The DER SubjectPublicKeyInfo bytes carried by a PEM public key. */
export function publicKeyPemToDer(pem: string): Uint8Array {
  if (pem.includes('PRIVATE KEY')) {
    throw new TypeError('Expected a public key, received a private key')
  }
  const match = PEM_PUBLIC_KEY.exec(pem)
  if (!match) {
    throw new TypeError('Not a PEM-encoded SubjectPublicKeyInfo public key')
  }
  return fromBase64(match[1].replace(/\s/g, ''))
}

/**
 * The account-wide public key identity: SHA-256 over the DER SubjectPublicKeyInfo.
 *
 * Clients recompute this locally from the PEM they received. A `fingerprint` field returned
 * by the API is a convenience, not evidence: a server that substitutes a public key can
 * substitute the field describing it just as easily.
 */
export async function publicKeyFingerprint(pem: string): Promise<string> {
  return sha256Hex(publicKeyPemToDer(pem))
}

/** Import a PEM public key for RSA-OAEP-SHA256 wrapping. */
export async function importRsaOaepPublicKey(pem: string): Promise<CryptoKey> {
  return subtle().importKey(
    'spki',
    publicKeyPemToDer(pem) as BufferSource,
    { name: 'RSA-OAEP', hash: 'SHA-256' },
    true,
    ['encrypt'],
  )
}

/** Import a PEM public key for RSA-PSS-SHA256 verification. */
export async function importRsaPssPublicKey(pem: string): Promise<CryptoKey> {
  return subtle().importKey(
    'spki',
    publicKeyPemToDer(pem) as BufferSource,
    { name: 'RSA-PSS', hash: 'SHA-256' },
    true,
    ['verify'],
  )
}

/**
 * Wrap key material to a recipient public key with RSA-OAEP-SHA256 and an **empty label**.
 *
 * The label is empty deliberately. A file's recovery wrapping is unwrapped by an offline or
 * HSM-hosted process, and OAEP label support is inconsistent across PKCS#11 stacks. A label
 * that the recovery workstation cannot reproduce would make that wrapping permanently
 * unopenable, and the recovery wrapping is the one envelope a client cannot self-test.
 */
export async function rsaOaepWrap(publicKey: CryptoKey, keyMaterial: Uint8Array): Promise<Uint8Array> {
  const wrapped = await subtle().encrypt({ name: 'RSA-OAEP' }, publicKey, keyMaterial as BufferSource)
  return new Uint8Array(wrapped)
}

/** Unwrap key material with the matching RSA private key. */
export async function rsaOaepUnwrap(privateKey: CryptoKey, wrapped: Uint8Array): Promise<Uint8Array> {
  try {
    const raw = await subtle().decrypt({ name: 'RSA-OAEP' }, privateKey, wrapped as BufferSource)
    return new Uint8Array(raw)
  } catch {
    throw new AuthenticationFailure('RSA-OAEP unwrapping failed')
  }
}

/** Sign a message with RSA-PSS-SHA256 and a 32-byte salt. */
export async function rsaPssSign(privateKey: CryptoKey, message: Uint8Array): Promise<Uint8Array> {
  const signature = await subtle().sign(
    { name: 'RSA-PSS', saltLength: RSA_PSS_SALT_BYTES },
    privateKey,
    message as BufferSource,
  )
  return new Uint8Array(signature)
}

/** Verify an RSA-PSS-SHA256 signature. */
export async function rsaPssVerify(
  publicKey: CryptoKey,
  message: Uint8Array,
  signature: Uint8Array,
): Promise<boolean> {
  return subtle().verify(
    { name: 'RSA-PSS', saltLength: RSA_PSS_SALT_BYTES },
    publicKey,
    signature as BufferSource,
    message as BufferSource,
  )
}
