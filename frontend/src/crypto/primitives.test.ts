import { readFileSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import { describe, expect, it } from 'vitest'

import { bytesToHex, hexToBytes } from './encoding'
import {
  AES_GCM_NONCE_BYTES,
  AES_GCM_TAG_BYTES,
  AuthenticationFailure,
  aesGcmDecryptDetached,
  aesGcmEncryptDetached,
  importAesGcmKey,
  importRsaOaepPublicKey,
  publicKeyFingerprint,
  publicKeyPemToDer,
  randomBytes,
  rsaOaepUnwrap,
  rsaOaepWrap,
  rsaPssSign,
  rsaPssVerify,
  sha256Hex,
} from './primitives'

/**
 * Known-answer vectors produced by python-cryptography. Checking this implementation
 * against an independent one is the point; a round trip against itself would pass even if
 * both directions were wrong in the same way.
 */
const vectorsPath = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  '../../../docs/crypto/test_vectors.json',
)
const vectors = JSON.parse(readFileSync(vectorsPath, 'utf8')) as {
  aes_256_gcm_detached: {
    case: string
    key_hex: string
    nonce_hex: string
    aad_hex: string
    plaintext_hex: string
    ciphertext_hex: string
    auth_tag_hex: string
  }[]
  sha256: { case: string; input_utf8: string; digest_hex: string }[]
  public_key_fingerprint: { case: string; public_key_pem: string; fingerprint_hex: string }[]
}

describe('SHA-256', () => {
  it.each(vectors.sha256)('matches the reference digest for $case', async (vector) => {
    expect(await sha256Hex(new TextEncoder().encode(vector.input_utf8))).toBe(vector.digest_hex)
  })
})

describe('AES-256-GCM with a detached tag', () => {
  it.each(vectors.aes_256_gcm_detached)('encrypts $case to the reference bytes', async (vector) => {
    const key = await importAesGcmKey(hexToBytes(vector.key_hex))
    const { ciphertext, authTag } = await aesGcmEncryptDetached({
      key,
      nonce: hexToBytes(vector.nonce_hex),
      plaintext: hexToBytes(vector.plaintext_hex),
      aad: hexToBytes(vector.aad_hex),
    })
    expect(bytesToHex(ciphertext)).toBe(vector.ciphertext_hex)
    expect(bytesToHex(authTag)).toBe(vector.auth_tag_hex)
  })

  it.each(vectors.aes_256_gcm_detached)('decrypts $case back to the plaintext', async (vector) => {
    const key = await importAesGcmKey(hexToBytes(vector.key_hex))
    const plaintext = await aesGcmDecryptDetached({
      key,
      nonce: hexToBytes(vector.nonce_hex),
      ciphertext: hexToBytes(vector.ciphertext_hex),
      authTag: hexToBytes(vector.auth_tag_hex),
      aad: hexToBytes(vector.aad_hex),
    })
    expect(bytesToHex(plaintext)).toBe(vector.plaintext_hex)
  })

  it('keeps the tag out of the ciphertext, as the upload size check requires', async () => {
    // file_service rejects an upload whose ciphertext length differs from plaintext_size.
    const key = await importAesGcmKey(randomBytes(32))
    const plaintext = randomBytes(1024)
    const { ciphertext, authTag } = await aesGcmEncryptDetached({
      key,
      nonce: randomBytes(AES_GCM_NONCE_BYTES),
      plaintext,
      aad: new Uint8Array(),
    })
    expect(ciphertext.length).toBe(plaintext.length)
    expect(authTag.length).toBe(AES_GCM_TAG_BYTES)
  })

  it('fails authentication when the AAD differs', async () => {
    const key = await importAesGcmKey(randomBytes(32))
    const nonce = randomBytes(AES_GCM_NONCE_BYTES)
    const { ciphertext, authTag } = await aesGcmEncryptDetached({
      key,
      nonce,
      plaintext: new TextEncoder().encode('confidential'),
      aad: new TextEncoder().encode('file-a'),
    })
    await expect(
      aesGcmDecryptDetached({
        key,
        nonce,
        ciphertext,
        authTag,
        aad: new TextEncoder().encode('file-b'),
      }),
    ).rejects.toBeInstanceOf(AuthenticationFailure)
  })

  it('fails authentication when a single ciphertext bit flips', async () => {
    const key = await importAesGcmKey(randomBytes(32))
    const nonce = randomBytes(AES_GCM_NONCE_BYTES)
    const aad = new Uint8Array()
    const { ciphertext, authTag } = await aesGcmEncryptDetached({
      key,
      nonce,
      plaintext: randomBytes(64),
      aad,
    })
    const tampered = Uint8Array.from(ciphertext)
    tampered[0] ^= 0x01
    await expect(
      aesGcmDecryptDetached({ key, nonce, ciphertext: tampered, authTag, aad }),
    ).rejects.toBeInstanceOf(AuthenticationFailure)
  })

  it('rejects a nonce or tag of the wrong length instead of silently adapting', async () => {
    const key = await importAesGcmKey(randomBytes(32))
    await expect(
      aesGcmEncryptDetached({
        key,
        nonce: randomBytes(16),
        plaintext: new Uint8Array(),
        aad: new Uint8Array(),
      }),
    ).rejects.toBeInstanceOf(RangeError)
    await expect(
      aesGcmDecryptDetached({
        key,
        nonce: randomBytes(AES_GCM_NONCE_BYTES),
        ciphertext: new Uint8Array(),
        authTag: randomBytes(8),
        aad: new Uint8Array(),
      }),
    ).rejects.toBeInstanceOf(RangeError)
  })

  it('accepts every key length a supported algorithm uses', async () => {
    for (const bytes of [16, 24, 32]) {
      await expect(importAesGcmKey(randomBytes(bytes))).resolves.toBeDefined()
    }
  })

  it('rejects a key length no supported algorithm uses', async () => {
    // 20 and 64 are the shapes a truncation or a concatenation bug produces. WebCrypto
    // rejects them too, but as an opaque OperationError at first use rather than here.
    for (const bytes of [0, 8, 20, 31, 33, 64]) {
      await expect(importAesGcmKey(randomBytes(bytes))).rejects.toBeInstanceOf(RangeError)
    }
  })
})

describe('public key identity', () => {
  const [vector] = vectors.public_key_fingerprint

  it('reproduces the reference fingerprint over DER SubjectPublicKeyInfo', async () => {
    expect(await publicKeyFingerprint(vector.public_key_pem)).toBe(vector.fingerprint_hex)
  })

  it('is stable across whitespace differences in the PEM', async () => {
    const reflowed = `${vector.public_key_pem.trim()}\n\n`
    expect(await publicKeyFingerprint(reflowed)).toBe(vector.fingerprint_hex)
  })

  it('refuses a private key or a non-PEM string', () => {
    expect(() => publicKeyPemToDer('-----BEGIN PRIVATE KEY-----\nAAA=\n-----END PRIVATE KEY-----')).toThrow(
      TypeError,
    )
    expect(() => publicKeyPemToDer('not a pem')).toThrow(TypeError)
  })
})

describe('RSA-OAEP-SHA256 key wrapping', () => {
  it('wraps and unwraps a 256-bit data encryption key', async () => {
    const pair = (await globalThis.crypto.subtle.generateKey(
      {
        name: 'RSA-OAEP',
        modulusLength: 2048,
        publicExponent: new Uint8Array([0x01, 0x00, 0x01]),
        hash: 'SHA-256',
      },
      true,
      ['encrypt', 'decrypt'],
    )) as CryptoKeyPair
    const dek = randomBytes(32)

    const wrapped = await rsaOaepWrap(pair.publicKey, dek)

    expect(wrapped.length).toBe(2048 / 8)
    expect(await rsaOaepUnwrap(pair.privateKey, wrapped)).toEqual(dek)
  })

  it('produces a different ciphertext each time, as OAEP randomization requires', async () => {
    const pair = (await globalThis.crypto.subtle.generateKey(
      {
        name: 'RSA-OAEP',
        modulusLength: 2048,
        publicExponent: new Uint8Array([0x01, 0x00, 0x01]),
        hash: 'SHA-256',
      },
      true,
      ['encrypt', 'decrypt'],
    )) as CryptoKeyPair
    const dek = randomBytes(32)
    const first = await rsaOaepWrap(pair.publicKey, dek)
    const second = await rsaOaepWrap(pair.publicKey, dek)
    expect(bytesToHex(first)).not.toBe(bytesToHex(second))
  })

  it('imports a PEM public key for wrapping', async () => {
    const key = await importRsaOaepPublicKey(vectors.public_key_fingerprint[0].public_key_pem)
    expect(key.algorithm.name).toBe('RSA-OAEP')
    expect((key.algorithm as RsaHashedKeyAlgorithm).modulusLength).toBe(3072)
  })

  it('reports a failed unwrap as an authentication failure', async () => {
    const pair = (await globalThis.crypto.subtle.generateKey(
      {
        name: 'RSA-OAEP',
        modulusLength: 2048,
        publicExponent: new Uint8Array([0x01, 0x00, 0x01]),
        hash: 'SHA-256',
      },
      true,
      ['encrypt', 'decrypt'],
    )) as CryptoKeyPair
    await expect(rsaOaepUnwrap(pair.privateKey, randomBytes(256))).rejects.toBeInstanceOf(
      AuthenticationFailure,
    )
  })
})

describe('RSA-PSS-SHA256 signatures', () => {
  it('signs and verifies with a 32-byte salt', async () => {
    const pair = (await globalThis.crypto.subtle.generateKey(
      {
        name: 'RSA-PSS',
        modulusLength: 2048,
        publicExponent: new Uint8Array([0x01, 0x00, 0x01]),
        hash: 'SHA-256',
      },
      true,
      ['sign', 'verify'],
    )) as CryptoKeyPair
    const digest = randomBytes(32)

    const signature = await rsaPssSign(pair.privateKey, digest)

    expect(signature.length).toBe(2048 / 8)
    expect(await rsaPssVerify(pair.publicKey, digest, signature)).toBe(true)

    const otherDigest = Uint8Array.from(digest)
    otherDigest[0] ^= 0x01
    expect(await rsaPssVerify(pair.publicKey, otherDigest, signature)).toBe(false)
  })
})
