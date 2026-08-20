import { describe, expect, it } from 'vitest'

import { fromBase64, toBase64 } from './encoding'
import { decryptFile, unwrapDek } from './file_envelope'
import { publicKeyFingerprint } from './primitives'
import {
  DEFAULT_MIME_TYPE,
  MAX_UPLOAD_BYTES,
  prepareUpload,
  resolveMimeType,
  type UploadRecipients,
  type UploadableFile,
} from './upload'

function fakeFile(name: string, bytes: Uint8Array, type?: string): UploadableFile {
  return {
    name,
    size: bytes.length,
    type,
    arrayBuffer: async () => bytes.slice().buffer,
  }
}

async function newRsaPairAndPem(): Promise<{ pair: CryptoKeyPair; pem: string }> {
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
  const spki = new Uint8Array(await globalThis.crypto.subtle.exportKey('spki', pair.publicKey))
  const body = toBase64(spki).replace(/(.{64})/g, '$1\n')
  return { pair, pem: `-----BEGIN PUBLIC KEY-----\n${body}\n-----END PUBLIC KEY-----\n` }
}

async function recipientsFor(ownerPem: string, recoveryPem: string): Promise<UploadRecipients> {
  return {
    ownerKeyId: '11111111-1111-4111-8111-111111111111',
    ownerPublicKeyPem: ownerPem,
    recoveryKeyId: '22222222-2222-4222-8222-222222222222',
    recoveryPublicKeyPem: recoveryPem,
    recoveryKeyFingerprint: await publicKeyFingerprint(recoveryPem),
  }
}

describe('resolveMimeType', () => {
  it('falls back when the browser reports nothing usable', () => {
    // File.type is empty for extensions the browser does not recognise, and the API
    // requires a well-formed media type.
    expect(resolveMimeType('')).toBe(DEFAULT_MIME_TYPE)
    expect(resolveMimeType(undefined)).toBe(DEFAULT_MIME_TYPE)
    expect(resolveMimeType('   ')).toBe(DEFAULT_MIME_TYPE)
    expect(resolveMimeType('unknown')).toBe(DEFAULT_MIME_TYPE)
  })

  it('lowercases and trims what the browser does report', () => {
    expect(resolveMimeType('Application/PDF')).toBe('application/pdf')
    expect(resolveMimeType(' text/plain ')).toBe('text/plain')
  })
})

describe('prepareUpload', () => {
  it('produces metadata that satisfies every shape the upload contract checks', async () => {
    const { pem: ownerPem } = await newRsaPairAndPem()
    const { pem: recoveryPem } = await newRsaPairAndPem()
    const plaintext = new TextEncoder().encode('quarterly numbers, confidential')

    const payload = await prepareUpload({
      file: fakeFile('report.pdf', plaintext, 'application/pdf'),
      recipients: await recipientsFor(ownerPem, recoveryPem),
    })

    const meta = payload.metadata
    expect(meta.original_filename).toBe('report.pdf')
    expect(meta.mime_type).toBe('application/pdf')
    expect(meta.encryption_algorithm).toBe('AES-256-GCM')
    expect(meta.key_wrapping_algorithm).toBe('RSA-OAEP-SHA256')
    expect(meta.envelope_version).toBe(1)
    expect(meta.aad_version).toBe(1)

    // file_service requires ciphertext length to equal plaintext_size exactly.
    expect(meta.plaintext_size).toBe(plaintext.length)
    expect(payload.ciphertext.length).toBe(plaintext.length)

    expect(fromBase64(meta.nonce)).toHaveLength(12)
    expect(fromBase64(meta.auth_tag)).toHaveLength(16)
    expect(fromBase64(meta.wrapped_file_key)).toHaveLength(256)
    expect(fromBase64(meta.recovery_wrapped_file_key)).toHaveLength(256)
    expect(meta.file_id).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/)
  })

  it('round trips: the owner can unwrap the key and recover the exact bytes', async () => {
    // The strongest check available without a server. It exercises the whole chain the
    // upload depends on: wrap, unwrap, AAD reconstruction, and authenticated decryption.
    const { pair: ownerPair, pem: ownerPem } = await newRsaPairAndPem()
    const { pem: recoveryPem } = await newRsaPairAndPem()
    const plaintext = new TextEncoder().encode('the quick brown fox jumps over the lazy dog')

    const payload = await prepareUpload({
      file: fakeFile('notes.txt', plaintext, 'text/plain'),
      recipients: await recipientsFor(ownerPem, recoveryPem),
    })

    const dek = await unwrapDek(ownerPair.privateKey, fromBase64(payload.metadata.wrapped_file_key))
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

    expect(new TextDecoder().decode(recovered)).toBe(
      'the quick brown fox jumps over the lazy dog',
    )
  })

  it('wraps the same key separately to the owner and the recovery key', async () => {
    const { pair: ownerPair, pem: ownerPem } = await newRsaPairAndPem()
    const { pair: recoveryPair, pem: recoveryPem } = await newRsaPairAndPem()

    const payload = await prepareUpload({
      file: fakeFile('a.bin', new Uint8Array([1, 2, 3])),
      recipients: await recipientsFor(ownerPem, recoveryPem),
    })

    const viaOwner = await unwrapDek(ownerPair.privateKey, fromBase64(payload.metadata.wrapped_file_key))
    const viaRecovery = await unwrapDek(
      recoveryPair.privateKey,
      fromBase64(payload.metadata.recovery_wrapped_file_key),
    )
    expect(viaRecovery).toEqual(viaOwner)
    expect(payload.metadata.wrapped_file_key).not.toBe(payload.metadata.recovery_wrapped_file_key)
  })

  it('defaults the MIME type when the browser reports none', async () => {
    const { pem } = await newRsaPairAndPem()
    const payload = await prepareUpload({
      file: fakeFile('archive.xyz', new Uint8Array([7])),
      recipients: await recipientsFor(pem, pem),
    })
    expect(payload.metadata.mime_type).toBe(DEFAULT_MIME_TYPE)
  })

  it('handles an empty file', async () => {
    const { pem } = await newRsaPairAndPem()
    const payload = await prepareUpload({
      file: fakeFile('empty.bin', new Uint8Array()),
      recipients: await recipientsFor(pem, pem),
    })
    expect(payload.metadata.plaintext_size).toBe(0)
    expect(payload.ciphertext).toHaveLength(0)
    expect(fromBase64(payload.metadata.auth_tag)).toHaveLength(16)
  })

  it('rejects an oversize file before doing any cryptographic work', async () => {
    const { pem } = await newRsaPairAndPem()
    const oversize: UploadableFile = {
      name: 'huge.iso',
      size: MAX_UPLOAD_BYTES + 1,
      type: 'application/octet-stream',
      arrayBuffer: async () => {
        throw new Error('must not read an oversize file into memory')
      },
    }
    await expect(
      prepareUpload({ file: oversize, recipients: await recipientsFor(pem, pem) }),
    ).rejects.toBeInstanceOf(RangeError)
  })

  it('surfaces a filename the API would reject rather than sending it', async () => {
    const { pem } = await newRsaPairAndPem()
    await expect(
      prepareUpload({
        file: fakeFile('bad/name.txt', new Uint8Array([1])),
        recipients: await recipientsFor(pem, pem),
      }),
    ).rejects.toThrow(/path separator/)
  })
})
