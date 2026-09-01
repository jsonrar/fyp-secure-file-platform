/**
 * WebCrypto wrappers for the algorithm suite.
 *
 * Every function here is a thin, testable primitive: it takes bytes and returns bytes.
 * Envelope construction, AAD layout, and business rules live in the modules above this one.
 */

import { chacha20poly1305 } from '@noble/ciphers/chacha.js'

import { bytesToHex, fromBase64 } from './encoding'

/**
 * The account key envelope size. The AMK and the private-key bundle are always AES-256-GCM;
 * only file content has a selectable strength, because only a file carries the algorithm it
 * was encrypted under in its own metadata.
 */
export const AES_KEY_BYTES = 32
export const AES_GCM_NONCE_BYTES = 12
export const AES_GCM_TAG_BYTES = 16
export const AES_GCM_TAG_BITS = AES_GCM_TAG_BYTES * 8

/**
 * The suites a file may be encrypted under, strongest-and-safest first.
 *
 * Two constructions, not one family. AES-GCM is a block cipher in counter mode authenticated
 * by GHASH; ChaCha20-Poly1305 is a stream cipher authenticated by Poly1305 (RFC 8439). They
 * fail differently and rest on different assumptions, which is the point of offering both --
 * the three AES entries differ only in key length.
 *
 * Every suite here is an AEAD. Nothing unauthenticated may be added: AES-CBC and AES-CTR are
 * available in WebCrypto and would discard the integrity guarantee the whole envelope rests
 * on. 3DES is excluded for the same reason plus its own -- it is not an AEAD at all, its
 * 8-byte block would break the shared nonce and tag lengths below, and NIST withdrew it for
 * encryption in 2023.
 *
 * The name is what `fileContentAad` commits to, so ciphertext written under one suite cannot
 * be reinterpreted as another without the tag failing.
 */
export const ENCRYPTION_SUITES = Object.freeze({
  'AES-256-GCM': Object.freeze({ keyBytes: 32, nonceBytes: 12, tagBytes: 16, platform: true }),
  'ChaCha20-Poly1305': Object.freeze({
    keyBytes: 32,
    nonceBytes: 12,
    tagBytes: 16,
    // Provided by @noble/ciphers rather than WebCrypto, so unlike the AES entries it is
    // available wherever this code runs and needs no capability probe.
    platform: false,
  }),
  'AES-192-GCM': Object.freeze({ keyBytes: 24, nonceBytes: 12, tagBytes: 16, platform: true }),
  'AES-128-GCM': Object.freeze({ keyBytes: 16, nonceBytes: 12, tagBytes: 16, platform: true }),
})

export const ENCRYPTION_ALGORITHMS = Object.freeze(
  Object.keys(ENCRYPTION_SUITES) as EncryptionAlgorithm[],
)

export type EncryptionAlgorithm = keyof typeof ENCRYPTION_SUITES

/** The raw key length each algorithm requires, in bytes. */
export const ENCRYPTION_KEY_BYTES: Readonly<Record<EncryptionAlgorithm, number>> = Object.freeze(
  Object.fromEntries(
    Object.entries(ENCRYPTION_SUITES).map(([name, suite]) => [name, suite.keyBytes]),
  ) as Record<EncryptionAlgorithm, number>,
)

/** What an upload uses unless the user chooses otherwise. */
export const DEFAULT_ENCRYPTION_ALGORITHM: EncryptionAlgorithm = 'AES-256-GCM'

/**
 * Narrow an arbitrary string to a known algorithm.
 *
 * Stored metadata is the server's word for what a file was encrypted under, and it reaches
 * the AAD. Anything unrecognised must be refused rather than passed through: an unknown name
 * cannot be decrypted, and admitting one would put attacker-chosen bytes into the AAD.
 */
export function isEncryptionAlgorithm(value: string): value is EncryptionAlgorithm {
  return (ENCRYPTION_ALGORITHMS as readonly string[]).includes(value)
}

/** The suite parameters for an algorithm name, rejecting anything not in the table. */
export function suiteFor(algorithm: string): (typeof ENCRYPTION_SUITES)[EncryptionAlgorithm] {
  if (!isEncryptionAlgorithm(algorithm)) {
    throw new RangeError(`Unsupported encryption algorithm: ${algorithm}`)
  }
  return ENCRYPTION_SUITES[algorithm]
}

/** The key length for an algorithm name, rejecting anything not in the table. */
export function keyBytesForAlgorithm(algorithm: string): number {
  return suiteFor(algorithm).keyBytes
}

/** The nonce length for an algorithm name. Every current suite uses 12, but none assumes it. */
export function nonceBytesForAlgorithm(algorithm: string): number {
  return suiteFor(algorithm).nonceBytes
}

/** Every key length any supported algorithm accepts. */
const LEGAL_KEY_BYTES: readonly number[] = Object.values(ENCRYPTION_KEY_BYTES)

let supported: Promise<EncryptionAlgorithm[]> | undefined

/**
 * The algorithms this browser can actually perform, strongest first.
 *
 * Probed rather than assumed, for the suites that come from the platform. AES-192 is absent
 * from some WebCrypto implementations -- Chromium never shipped it -- and a key length the
 * browser rejects surfaces as a bare `OperationError` at encryption time, after the user has
 * chosen it and picked a file. ChaCha20-Poly1305 is not probed: it is a library, so it works
 * wherever this code runs. Cached, because the answer cannot change within a page.
 */
export function supportedEncryptionAlgorithms(): Promise<EncryptionAlgorithm[]> {
  supported ??= (async () => {
    const usable = await Promise.all(
      ENCRYPTION_ALGORITHMS.map(async (algorithm) => {
        if (!ENCRYPTION_SUITES[algorithm].platform) return algorithm
        try {
          await importAesGcmKey(new Uint8Array(ENCRYPTION_KEY_BYTES[algorithm]))
          return algorithm
        } catch {
          return undefined
        }
      }),
    )
    const available = usable.filter((a): a is EncryptionAlgorithm => a !== undefined)
    // AES-256 is required, not optional: without it there is no default to fall back to.
    if (!available.includes(DEFAULT_ENCRYPTION_ALGORITHM)) {
      throw new Error('This browser cannot perform AES-256-GCM; encryption is unavailable')
    }
    return available
  })()
  return supported
}

/**
 * ChaCha20-Poly1305 parameters, from RFC 8439.
 *
 * Deliberately identical in shape to AES-GCM above: a 32-byte key, a 12-byte nonce, and a
 * 16-byte tag. That is not a coincidence to rely on blindly, but it is what lets one stored
 * column layout, one database CHECK constraint, and one envelope serve both constructions.
 */
export const CHACHA20_KEY_BYTES = 32
export const CHACHA20_NONCE_BYTES = 12
export const CHACHA20_TAG_BYTES = 16

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
  if (!LEGAL_KEY_BYTES.includes(raw.length)) {
    throw new RangeError(
      `AES-GCM key must be ${LEGAL_KEY_BYTES.join(', ')} bytes, received ${raw.length}`,
    )
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

/**
 * ChaCha20-Poly1305 encryption with the tag detached, mirroring {@link aesGcmEncryptDetached}.
 *
 * WebCrypto has no ChaCha20-Poly1305, so this uses @noble/ciphers — audited, dependency-free,
 * and a pure TypeScript implementation of RFC 8439.
 *
 * **The key is raw bytes here, not a `CryptoKey`.** The AES path imports its key as
 * non-extractable, so a later bug cannot serialise it into a log line or a request body; a
 * library implementation cannot offer that, because it must read the key material to work.
 * Keep a ChaCha key in a local as briefly as the AES path keeps its `CryptoKey`, and never
 * put one anywhere a value could be inspected or persisted.
 */
export async function chacha20Poly1305EncryptDetached(params: {
  key: Uint8Array
  nonce: Uint8Array
  plaintext: Uint8Array
  aad: Uint8Array
}): Promise<AesGcmCiphertext> {
  const { key, nonce, plaintext, aad } = params
  if (key.length !== CHACHA20_KEY_BYTES) {
    throw new RangeError(`ChaCha20-Poly1305 key must be ${CHACHA20_KEY_BYTES} bytes`)
  }
  if (nonce.length !== CHACHA20_NONCE_BYTES) {
    throw new RangeError(`ChaCha20-Poly1305 nonce must be ${CHACHA20_NONCE_BYTES} bytes`)
  }
  // noble appends the tag, exactly as WebCrypto does, so the split below is the same.
  const joined = chacha20poly1305(key, nonce, aad).encrypt(plaintext)
  return {
    ciphertext: joined.slice(0, joined.length - CHACHA20_TAG_BYTES),
    authTag: joined.slice(joined.length - CHACHA20_TAG_BYTES),
  }
}

/** ChaCha20-Poly1305 decryption, rejoining the detached tag before verification. */
export async function chacha20Poly1305DecryptDetached(params: {
  key: Uint8Array
  nonce: Uint8Array
  ciphertext: Uint8Array
  authTag: Uint8Array
  aad: Uint8Array
}): Promise<Uint8Array> {
  const { key, nonce, ciphertext, authTag, aad } = params
  if (key.length !== CHACHA20_KEY_BYTES) {
    throw new RangeError(`ChaCha20-Poly1305 key must be ${CHACHA20_KEY_BYTES} bytes`)
  }
  if (nonce.length !== CHACHA20_NONCE_BYTES) {
    throw new RangeError(`ChaCha20-Poly1305 nonce must be ${CHACHA20_NONCE_BYTES} bytes`)
  }
  if (authTag.length !== CHACHA20_TAG_BYTES) {
    throw new RangeError(`ChaCha20-Poly1305 tag must be ${CHACHA20_TAG_BYTES} bytes`)
  }
  const joined = concat(ciphertext, authTag)
  try {
    return chacha20poly1305(key, nonce, aad).decrypt(joined)
  } catch {
    // Raised as the same type the AES path raises, so callers handle one failure mode
    // rather than two. As with GCM, a failure does not say which of a wrong key, a
    // substituted envelope, or corrupt ciphertext caused it.
    throw new AuthenticationFailure('ChaCha20-Poly1305 authentication failed')
  }
}

function concat(a: Uint8Array, b: Uint8Array): Uint8Array {
  const out = new Uint8Array(a.length + b.length)
  out.set(a, 0)
  out.set(b, a.length)
  return out
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
const PEM_PRIVATE_KEY = /-----BEGIN PRIVATE KEY-----([\s\S]+?)-----END PRIVATE KEY-----/

/**
 * The DER PKCS#8 bytes carried by a PEM private key.
 *
 * The counterpart of `publicKeyPemToDer`, for the key file the registration page hands the
 * user once and tells them to keep. Only PKCS#8 (`BEGIN PRIVATE KEY`) is accepted:
 * `BEGIN RSA PRIVATE KEY` is PKCS#1, which WebCrypto cannot import, and it is worth saying
 * so rather than failing later inside `importKey` with a DataError.
 */
export function privateKeyPemToDer(pem: string): Uint8Array {
  if (/-----BEGIN RSA PRIVATE KEY-----/.test(pem)) {
    throw new TypeError(
      'This is a PKCS#1 private key. SecureView issues PKCS#8 keys, which begin with "BEGIN PRIVATE KEY".',
    )
  }
  const match = PEM_PRIVATE_KEY.exec(pem)
  if (!match) {
    throw new TypeError('Not a PEM-encoded PKCS#8 private key')
  }
  return fromBase64(match[1].replace(/\s/g, ''))
}

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

/**
 * Import a PKCS8 DER private key for RSA-OAEP-SHA256 unwrapping.
 *
 * Non-extractable: once the key is imported the page can decrypt with it but can no
 * longer read the bytes back out, so a later bug cannot serialise the account private key
 * into a log line, an error report, or a request body.
 */
export async function importRsaOaepPrivateKey(pkcs8Der: Uint8Array): Promise<CryptoKey> {
  return subtle().importKey(
    'pkcs8',
    pkcs8Der as BufferSource,
    { name: 'RSA-OAEP', hash: 'SHA-256' },
    false,
    ['decrypt'],
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
