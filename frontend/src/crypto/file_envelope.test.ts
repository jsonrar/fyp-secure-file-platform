import { readFileSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import { describe, expect, it } from 'vitest'

import { bytesToHex, fromBase64, hexToBytes } from './encoding'
import {
  buildUploadPayload,
  decryptFile,
  encryptFile,
  encryptFileWithMaterial,
  fileContentAad,
  normalizeIdentity,
  unwrapDek,
  verifyDekOpensFile,
  wrapDekTo,
  type FileIdentity,
} from './file_envelope'
import { AuthenticationFailure, publicKeyFingerprint } from './primitives'

const vectorsPath = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  '../../../docs/crypto/test_vectors.json',
)
const vectors = JSON.parse(readFileSync(vectorsPath, 'utf8')) as {
  file_content_aad: {
    case: string
    file_id: string
    envelope_version: number
    aad_version: number
    encryption_algorithm: string
    plaintext_size: number
    original_filename: string
    mime_type: string
    aad_hex: string
  }[]
  file_envelope: {
    case: string
    file_id: string
    envelope_version: number
    aad_version: number
    encryption_algorithm: string
    plaintext_size: number
    original_filename: string
    mime_type: string
    dek_hex: string
    nonce_hex: string
    plaintext_hex: string
    ciphertext_hex: string
    auth_tag_hex: string
  }[]
  public_key_fingerprint: { public_key_pem: string }[]
}

const identityOf = (vector: {
  file_id: string
  envelope_version: number
  aad_version: number
  encryption_algorithm: string
  plaintext_size: number
  original_filename: string
  mime_type: string
}): FileIdentity => ({
  fileId: vector.file_id,
  originalFilename: vector.original_filename,
  plaintextSize: vector.plaintext_size,
  mimeType: vector.mime_type,
  envelopeVersion: vector.envelope_version,
  aadVersion: vector.aad_version,
  encryptionAlgorithm: vector.encryption_algorithm,
})

describe('AAD-3 construction', () => {
  it.each(vectors.file_content_aad)('matches the reference bytes for $case', (vector) => {
    expect(bytesToHex(fileContentAad(identityOf(vector)))).toBe(vector.aad_hex)
  })

  it('is unchanged by NFD input, because the backend stores NFC', () => {
    const nfc = vectors.file_content_aad.find((v) => v.case === 'nfd-normalized')!
    const asNfd = { ...nfc, original_filename: nfc.original_filename.normalize('NFD') }
    const asNfcInput = { ...nfc, original_filename: nfc.original_filename.normalize('NFC') }
    expect(bytesToHex(fileContentAad(identityOf(asNfd)))).toBe(nfc.aad_hex)
    expect(bytesToHex(fileContentAad(identityOf(asNfcInput)))).toBe(nfc.aad_hex)
  })

  it('lowercases the MIME type', () => {
    const base = vectors.file_content_aad[0]
    const upper = fileContentAad(identityOf({ ...base, mime_type: base.mime_type.toUpperCase() }))
    expect(bytesToHex(upper)).toBe(base.aad_hex)
  })

  it('changes when any bound field changes', () => {
    const base = vectors.file_content_aad[0]
    const original = base.aad_hex
    expect(bytesToHex(fileContentAad(identityOf({ ...base, original_filename: 'other.pdf' })))).not.toBe(
      original,
    )
    expect(bytesToHex(fileContentAad(identityOf({ ...base, mime_type: 'text/plain' })))).not.toBe(
      original,
    )
    expect(bytesToHex(fileContentAad(identityOf({ ...base, plaintext_size: 1025 })))).not.toBe(
      original,
    )
    expect(
      bytesToHex(
        fileContentAad(identityOf({ ...base, file_id: '00000000-0000-4000-8000-000000000000' })),
      ),
    ).not.toBe(original)
  })

  it('depends on nothing per-recipient, so a share recipient rebuilds the same bytes', () => {
    // The API returns the caller's own key_id in the envelope. If the AAD depended on it,
    // every shared file would be undecryptable for the recipient.
    const base = vectors.file_content_aad[0]
    const owner = fileContentAad(identityOf(base))
    const recipient = fileContentAad(identityOf({ ...base }))
    expect(bytesToHex(owner)).toBe(bytesToHex(recipient))
  })
})

describe('file envelope against reference vectors', () => {
  it.each(vectors.file_envelope)('encrypts $case to the reference ciphertext', async (vector) => {
    const envelope = await encryptFileWithMaterial({
      plaintext: hexToBytes(vector.plaintext_hex),
      identity: identityOf(vector),
      dek: hexToBytes(vector.dek_hex),
      nonce: hexToBytes(vector.nonce_hex),
    })
    expect(bytesToHex(envelope.ciphertext)).toBe(vector.ciphertext_hex)
    expect(bytesToHex(envelope.authTag)).toBe(vector.auth_tag_hex)
    expect(envelope.ciphertext.length).toBe(vector.plaintext_size)
  })

  it.each(vectors.file_envelope)('decrypts $case back to the plaintext', async (vector) => {
    const plaintext = await decryptFile({
      identity: identityOf(vector),
      dek: hexToBytes(vector.dek_hex),
      nonce: hexToBytes(vector.nonce_hex),
      ciphertext: hexToBytes(vector.ciphertext_hex),
      authTag: hexToBytes(vector.auth_tag_hex),
    })
    expect(bytesToHex(plaintext)).toBe(vector.plaintext_hex)
  })
})

describe('metadata tampering is detected', () => {
  const vector = vectors.file_envelope[0]
  const sealed = {
    dek: hexToBytes(vector.dek_hex),
    nonce: hexToBytes(vector.nonce_hex),
    ciphertext: hexToBytes(vector.ciphertext_hex),
    authTag: hexToBytes(vector.auth_tag_hex),
  }

  it('rejects a rewritten filename', async () => {
    await expect(
      decryptFile({ ...sealed, identity: identityOf({ ...vector, original_filename: 'invoice.pdf' }) }),
    ).rejects.toBeInstanceOf(AuthenticationFailure)
  })

  it('rejects a rewritten MIME type', async () => {
    await expect(
      decryptFile({ ...sealed, identity: identityOf({ ...vector, mime_type: 'text/html' }) }),
    ).rejects.toBeInstanceOf(AuthenticationFailure)
  })

  it('rejects a rewritten file id', async () => {
    await expect(
      decryptFile({
        ...sealed,
        identity: identityOf({ ...vector, file_id: '00000000-0000-4000-8000-000000000000' }),
      }),
    ).rejects.toBeInstanceOf(AuthenticationFailure)
  })

  it('rejects a flipped ciphertext bit', async () => {
    const tampered = Uint8Array.from(sealed.ciphertext)
    tampered[0] ^= 0x01
    await expect(
      decryptFile({ ...sealed, ciphertext: tampered, identity: identityOf(vector) }),
    ).rejects.toBeInstanceOf(AuthenticationFailure)
  })
})

describe('encryptFile', () => {
  const plaintext = new TextEncoder().encode('quarterly numbers, confidential')

  it('produces a self-tested envelope whose ciphertext matches plaintext_size', async () => {
    const envelope = await encryptFile({
      plaintext,
      originalFilename: 'report.pdf',
      mimeType: 'application/pdf',
    })
    expect(envelope.ciphertext.length).toBe(plaintext.length)
    expect(envelope.identity.plaintextSize).toBe(plaintext.length)
    expect(envelope.nonce).toHaveLength(12)
    expect(envelope.authTag).toHaveLength(16)
    expect(envelope.dek).toHaveLength(32)
  })

  it('uses fresh key material on every call', async () => {
    const first = await encryptFile({
      plaintext,
      originalFilename: 'a.pdf',
      mimeType: 'application/pdf',
    })
    const second = await encryptFile({
      plaintext,
      originalFilename: 'a.pdf',
      mimeType: 'application/pdf',
    })
    expect(bytesToHex(first.dek)).not.toBe(bytesToHex(second.dek))
    expect(bytesToHex(first.nonce)).not.toBe(bytesToHex(second.nonce))
    expect(first.identity.fileId).not.toBe(second.identity.fileId)
  })

  it('round trips through decryptFile', async () => {
    const envelope = await encryptFile({
      plaintext,
      originalFilename: 'report.pdf',
      mimeType: 'application/pdf',
    })
    const recovered = await decryptFile({
      identity: envelope.identity,
      dek: envelope.dek,
      nonce: envelope.nonce,
      ciphertext: envelope.ciphertext,
      authTag: envelope.authTag,
    })
    expect(new TextDecoder().decode(recovered)).toBe('quarterly numbers, confidential')
  })

  it('handles an empty file', async () => {
    const envelope = await encryptFile({
      plaintext: new Uint8Array(),
      originalFilename: 'empty.bin',
      mimeType: 'application/octet-stream',
    })
    expect(envelope.ciphertext).toHaveLength(0)
    expect(envelope.authTag).toHaveLength(16)
  })
})

describe('identity normalization mirrors the backend rules', () => {
  const base: FileIdentity = {
    fileId: '3f2a1b4c-5d6e-4f70-8192-a3b4c5d6e7f8',
    originalFilename: 'report.pdf',
    plaintextSize: 10,
    mimeType: 'application/pdf',
  }

  it('normalizes to NFC and lowercases the MIME type', () => {
    const normalized = normalizeIdentity({
      ...base,
      originalFilename: 'résumé.pdf',
      mimeType: 'APPLICATION/PDF',
    })
    expect(normalized.originalFilename).toBe('résumé.pdf')
    expect(normalized.mimeType).toBe('application/pdf')
  })

  it.each([
    ['surrounding whitespace', ' report.pdf'],
    ['a path separator', 'dir/report.pdf'],
    ['a backslash', 'dir\\report.pdf'],
    ['a NUL byte', 'report\u0000.pdf'],
    ['a C0 control character', 'report\u0007.pdf'],
    ['a trailing period', 'report.'],
    ['a trailing space', 'report '],
    ['a bare dot', '.'],
    ['a double dot', '..'],
    ['an empty name', ''],
  ])('rejects a filename with %s', (_label, filename) => {
    expect(() => normalizeIdentity({ ...base, originalFilename: filename })).toThrow()
  })

  it.each([
    ['a parameter', 'text/plain; charset=utf-8'],
    ['no subtype', 'application'],
    ['a leading slash', '/pdf'],
    ['an empty value', ''],
  ])('rejects a MIME type with %s', (_label, mimeType) => {
    expect(() => normalizeIdentity({ ...base, mimeType })).toThrow(TypeError)
  })

  it('rejects a negative or non-integer size', () => {
    expect(() => normalizeIdentity({ ...base, plaintextSize: -1 })).toThrow(RangeError)
    expect(() => normalizeIdentity({ ...base, plaintextSize: 1.5 })).toThrow(RangeError)
  })
})

describe('DEK wrapping and upload payload', () => {
  const ownerPem = vectors.public_key_fingerprint[0].public_key_pem

  async function newRsaPair(): Promise<CryptoKeyPair> {
    return (await globalThis.crypto.subtle.generateKey(
      {
        name: 'RSA-OAEP',
        modulusLength: 2048,
        publicExponent: new Uint8Array([0x01, 0x00, 0x01]),
        hash: 'SHA-256',
      },
      true,
      ['encrypt', 'decrypt'],
    )) as CryptoKeyPair
  }

  it('wraps a DEK to a PEM public key at the modulus size', async () => {
    const envelope = await encryptFile({
      plaintext: new Uint8Array([1, 2, 3]),
      originalFilename: 'a.bin',
      mimeType: 'application/octet-stream',
    })
    const wrapped = await wrapDekTo(ownerPem, envelope.dek)
    expect(wrapped).toHaveLength(3072 / 8)
  })

  it('unwraps back to the same DEK', async () => {
    const pair = await newRsaPair()
    const spki = new Uint8Array(await globalThis.crypto.subtle.exportKey('spki', pair.publicKey))
    let base64 = ''
    for (const byte of spki) base64 += String.fromCharCode(byte)
    const pem = `-----BEGIN PUBLIC KEY-----\n${btoa(base64).replace(/(.{64})/g, '$1\n')}\n-----END PUBLIC KEY-----\n`

    const envelope = await encryptFile({
      plaintext: new Uint8Array([9, 9, 9]),
      originalFilename: 'a.bin',
      mimeType: 'application/octet-stream',
    })
    const wrapped = await wrapDekTo(pem, envelope.dek)

    expect(await unwrapDek(pair.privateKey, wrapped)).toEqual(envelope.dek)
  })

  it('assembles metadata the upload contract accepts', async () => {
    const envelope = await encryptFile({
      plaintext: new TextEncoder().encode('hello'),
      originalFilename: 'hello.txt',
      mimeType: 'text/plain',
    })
    const payload = await buildUploadPayload({
      envelope,
      ownerKeyId: '11111111-1111-4111-8111-111111111111',
      ownerPublicKeyPem: ownerPem,
      recoveryKeyId: '22222222-2222-4222-8222-222222222222',
      recoveryPublicKeyPem: ownerPem,
    })

    expect(payload.metadata.encryption_algorithm).toBe('AES-256-GCM')
    expect(payload.metadata.key_wrapping_algorithm).toBe('RSA-OAEP-SHA256')
    expect(payload.metadata.envelope_version).toBe(1)
    expect(payload.metadata.aad_version).toBe(1)
    expect(payload.metadata.plaintext_size).toBe(5)
    expect(payload.ciphertext).toHaveLength(5)

    // Every binary field must survive the API's canonical-Base64 check at its exact length.
    expect(fromBase64(payload.metadata.nonce)).toHaveLength(12)
    expect(fromBase64(payload.metadata.auth_tag)).toHaveLength(16)
    expect(fromBase64(payload.metadata.wrapped_file_key)).toHaveLength(384)
    expect(fromBase64(payload.metadata.recovery_wrapped_file_key)).toHaveLength(384)
  })

  it('reports the recovery key fingerprint so the caller can pin it', async () => {
    const envelope = await encryptFile({
      plaintext: new Uint8Array([1]),
      originalFilename: 'a.bin',
      mimeType: 'application/octet-stream',
    })
    const payload = await buildUploadPayload({
      envelope,
      ownerKeyId: '11111111-1111-4111-8111-111111111111',
      ownerPublicKeyPem: ownerPem,
      recoveryKeyId: '22222222-2222-4222-8222-222222222222',
      recoveryPublicKeyPem: ownerPem,
    })
    expect(payload.recoveryKeyFingerprint).toBe(await publicKeyFingerprint(ownerPem))
  })

  it('wraps the owner and recovery copies to different ciphertexts', async () => {
    const envelope = await encryptFile({
      plaintext: new Uint8Array([1]),
      originalFilename: 'a.bin',
      mimeType: 'application/octet-stream',
    })
    const payload = await buildUploadPayload({
      envelope,
      ownerKeyId: '11111111-1111-4111-8111-111111111111',
      ownerPublicKeyPem: ownerPem,
      recoveryKeyId: '22222222-2222-4222-8222-222222222222',
      recoveryPublicKeyPem: ownerPem,
    })
    // Same key here, but OAEP is randomized, so the two wrappings must still differ.
    expect(payload.metadata.wrapped_file_key).not.toBe(payload.metadata.recovery_wrapped_file_key)
  })
})

describe('verifyDekOpensFile', () => {
  it('accepts the correct DEK and rejects a wrong one before a share is submitted', async () => {
    const envelope = await encryptFile({
      plaintext: new TextEncoder().encode('shared document'),
      originalFilename: 'shared.txt',
      mimeType: 'text/plain',
    })
    const sealed = {
      identity: envelope.identity,
      nonce: envelope.nonce,
      ciphertext: envelope.ciphertext,
      authTag: envelope.authTag,
    }

    expect(await verifyDekOpensFile({ ...sealed, dek: envelope.dek })).toBe(true)

    const wrongDek = Uint8Array.from(envelope.dek)
    wrongDek[0] ^= 0x01
    expect(await verifyDekOpensFile({ ...sealed, dek: wrongDek })).toBe(false)
  })
})
