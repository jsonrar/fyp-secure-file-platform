import { beforeEach, describe, expect, it, vi } from 'vitest'

const get = vi.fn()
const post = vi.fn()

vi.mock('./http', () => ({
  http: {
    get: (...args: unknown[]) => get(...args),
    post: (...args: unknown[]) => post(...args),
  },
}))

import { avatarApi } from './avatar_api'
import { shelfApi } from './shelf_api'
import { fileApi } from './file_api'

describe('avatarApi', () => {
  beforeEach(() => {
    get.mockReset()
    post.mockReset()
    get.mockResolvedValue({ data: new ArrayBuffer(0), headers: {} })
    post.mockResolvedValue({ data: { data: {} } })
  })

  it('uploads multipart to /auth/avatar/upload', async () => {
    const file = new Blob(['x'], { type: 'image/png' })
    await avatarApi.upload(file)
    expect(post).toHaveBeenCalledWith('/auth/avatar/upload', expect.any(FormData))
  })

  it('fetches avatar bytes as arraybuffer', async () => {
    await avatarApi.getBytes()
    expect(get).toHaveBeenCalledWith('/auth/avatar', { responseType: 'arraybuffer' })
  })

  it('deletes via POST /auth/avatar/delete', async () => {
    await avatarApi.delete()
    expect(post).toHaveBeenCalledWith('/auth/avatar/delete')
  })
})

describe('shelfApi', () => {
  beforeEach(() => {
    get.mockReset()
    post.mockReset()
    get.mockResolvedValue({ data: { data: { shelves: [] } } })
    post.mockResolvedValue({ data: { data: {} } })
  })

  it('lists shelves', async () => {
    await shelfApi.list()
    expect(get).toHaveBeenCalledWith('/shelves')
  })

  it('creates, renames, and deletes shelves', async () => {
    await shelfApi.create('Work')
    expect(post).toHaveBeenCalledWith('/shelves', { name: 'Work' })

    await shelfApi.rename('shelf-1', 'Archive')
    expect(post).toHaveBeenCalledWith('/shelves/shelf-1/rename', { name: 'Archive' })

    await shelfApi.delete('shelf-1')
    expect(post).toHaveBeenCalledWith('/shelves/shelf-1/delete')
  })
})

describe('fileApi shelf helpers', () => {
  beforeEach(() => {
    get.mockReset()
    post.mockReset()
    get.mockResolvedValue({ data: { data: { items: [], page: 1, page_size: 25, total: 0 } } })
    post.mockResolvedValue({ data: { data: {} } })
  })

  it('passes shelf list filters and move body', async () => {
    await fileApi.listFiles({ page: 1, page_size: 25, root_only: true })
    expect(get).toHaveBeenCalledWith('/files', {
      params: { page: 1, page_size: 25, root_only: true },
    })

    await fileApi.move('file-1', 'shelf-1')
    expect(post).toHaveBeenCalledWith('/files/file-1/move', { shelf_id: 'shelf-1' })

    await fileApi.move('file-1', null)
    expect(post).toHaveBeenCalledWith('/files/file-1/move', { shelf_id: null })
  })
})
