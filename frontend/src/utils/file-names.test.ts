import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { fileApi } from '@/api/file_api'

import { fallbackFileLabel, forgetFileNames, resolveFileNames } from './file-names'

const summary = (id: string, name: string) => ({
  file_id: id,
  original_filename: name,
  plaintext_size: 1,
  ciphertext_size: 1,
  mime_type: 'application/pdf',
  encryption_algorithm: 'AES-256-GCM',
  status: 'ACTIVE',
  owner: true,
  created_at: '2026-08-26T00:00:00Z',
  updated_at: '2026-08-26T00:00:00Z',
})

const listResponse = (items: ReturnType<typeof summary>[]) => ({
  data: { success: true, status: 'ok', message: '', code: 200, data: { items, page: 1, page_size: 100, total: items.length } },
})

const fileResponse = (id: string, name: string) => ({
  data: { success: true, status: 'ok', message: '', code: 200, data: summary(id, name) },
})

beforeEach(() => {
  forgetFileNames()
  vi.restoreAllMocks()
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('resolveFileNames', () => {
  it('names every file from the single list call', async () => {
    const list = vi
      .spyOn(fileApi, 'listFiles')
      .mockResolvedValue(listResponse([summary('a', 'minutes.pdf'), summary('b', 'notes.txt')]) as never)
    const getFile = vi.spyOn(fileApi, 'getFile')

    const names = await resolveFileNames(['a', 'b'])

    expect(names.get('a')).toBe('minutes.pdf')
    expect(names.get('b')).toBe('notes.txt')
    // The point of listing first: eight files should not cost eight requests.
    expect(list).toHaveBeenCalledOnce()
    expect(getFile).not.toHaveBeenCalled()
  })

  it('falls back to a per-file lookup for what the list did not cover', async () => {
    vi.spyOn(fileApi, 'listFiles').mockResolvedValue(listResponse([summary('a', 'minutes.pdf')]) as never)
    const getFile = vi
      .spyOn(fileApi, 'getFile')
      .mockResolvedValue(fileResponse('shared', 'from-a-colleague.pdf') as never)

    const names = await resolveFileNames(['a', 'shared'])

    expect(names.get('shared')).toBe('from-a-colleague.pdf')
    expect(getFile).toHaveBeenCalledExactlyOnceWith('shared')
  })

  it('leaves a deleted file unnamed instead of failing the whole resolve', async () => {
    // Audit entries outlive the files they describe, and what happened to a file is worth
    // showing after the file is gone.
    vi.spyOn(fileApi, 'listFiles').mockResolvedValue(listResponse([summary('a', 'minutes.pdf')]) as never)
    vi.spyOn(fileApi, 'getFile').mockRejectedValue(new Error('404'))

    const names = await resolveFileNames(['a', 'deleted-one'])

    expect(names.get('a')).toBe('minutes.pdf')
    expect(names.has('deleted-one')).toBe(false)
  })

  it('still resolves when the list call fails outright', async () => {
    vi.spyOn(fileApi, 'listFiles').mockRejectedValue(new Error('500'))
    vi.spyOn(fileApi, 'getFile').mockResolvedValue(fileResponse('a', 'minutes.pdf') as never)

    const names = await resolveFileNames(['a'])

    expect(names.get('a')).toBe('minutes.pdf')
  })

  it('does not ask twice for a name it already has', async () => {
    const list = vi
      .spyOn(fileApi, 'listFiles')
      .mockResolvedValue(listResponse([summary('a', 'minutes.pdf')]) as never)

    await resolveFileNames(['a'])
    const names = await resolveFileNames(['a'])

    expect(names.get('a')).toBe('minutes.pdf')
    expect(list).toHaveBeenCalledOnce()
  })

  it('asks for nothing when there is nothing to resolve', async () => {
    const list = vi.spyOn(fileApi, 'listFiles')

    // 'unknown' is what the page uses for a log row with no file_id; it is not an id.
    const names = await resolveFileNames(['unknown', ''])

    expect(names.size).toBe(0)
    expect(list).not.toHaveBeenCalled()
  })

  it('deduplicates ids that appear on many log rows', async () => {
    // One file with twenty audit entries is the normal case, not an edge case.
    const getFile = vi.spyOn(fileApi, 'getFile').mockResolvedValue(fileResponse('a', 'minutes.pdf') as never)
    vi.spyOn(fileApi, 'listFiles').mockResolvedValue(listResponse([]) as never)

    await resolveFileNames(['a', 'a', 'a', 'a'])

    expect(getFile).toHaveBeenCalledOnce()
  })
})

describe('fallbackFileLabel', () => {
  it('shortens an id into something readable but still distinct', () => {
    expect(fallbackFileLabel('f5ba34ea-e701-4e1e-9fa8-bf48406054fd')).toBe('File f5ba34ea')
  })

  it('names a log row that has no file at all', () => {
    expect(fallbackFileLabel('unknown')).toBe('Unknown file')
    expect(fallbackFileLabel('')).toBe('Unknown file')
  })
})
