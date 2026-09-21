import { afterEach, describe, expect, it, vi } from 'vitest'

import { auditApi } from '@/api/audit_api'

import { fetchAuditTrail, MAX_ROWS, PAGE_SIZE } from './audit-trail'

const row = (i: number) => ({
  action: 'FILE_DOWNLOAD_AUTHORIZED',
  resource_type: 'FILE',
  resource_id: `file-${i}`,
  actor_user_id: 'u',
  actor_username: 'waldo',
  target_user_id: null,
  target_username: null,
  result: 'SUCCESS',
  description: null,
  metadata: {},
  created_at: '2026-09-01T00:00:00Z',
})

const page = (count: number, hasMore: boolean, from = 0) => ({
  data: {
    success: true,
    status: 'ok',
    message: '',
    code: 200,
    data: {
      logs: Array.from({ length: count }, (_, i) => row(from + i)),
      limit: PAGE_SIZE,
      offset: from,
      has_more: hasMore,
    },
  },
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('fetchAuditTrail', () => {
  it('stops after one request when the server says there is no more', async () => {
    const list = vi.spyOn(auditApi, 'listLogs').mockResolvedValue(page(12, false) as never)

    const trail = await fetchAuditTrail()

    expect(trail.logs).toHaveLength(12)
    expect(trail.partial).toBe(false)
    expect(list).toHaveBeenCalledOnce()
  })

  it('keeps going while more remain', async () => {
    // The bug this exists for: the stats read one page and looked like totals. On a real
    // account, page one held four distinct files where the whole trail held eight.
    const list = vi
      .spyOn(auditApi, 'listLogs')
      .mockResolvedValueOnce(page(PAGE_SIZE, true, 0) as never)
      .mockResolvedValueOnce(page(PAGE_SIZE, true, PAGE_SIZE) as never)
      .mockResolvedValueOnce(page(30, false, PAGE_SIZE * 2) as never)

    const trail = await fetchAuditTrail()

    expect(trail.logs).toHaveLength(PAGE_SIZE * 2 + 30)
    expect(trail.partial).toBe(false)
    expect(list).toHaveBeenCalledTimes(3)
  })

  it('asks for each page by offset, not the same one repeatedly', async () => {
    const list = vi
      .spyOn(auditApi, 'listLogs')
      .mockResolvedValueOnce(page(PAGE_SIZE, true, 0) as never)
      .mockResolvedValueOnce(page(5, false, PAGE_SIZE) as never)

    await fetchAuditTrail()

    expect(list).toHaveBeenNthCalledWith(1, { limit: PAGE_SIZE, offset: 0 })
    expect(list).toHaveBeenNthCalledWith(2, { limit: PAGE_SIZE, offset: PAGE_SIZE })
  })

  it('gives up at the cap and says the totals are partial', async () => {
    // An account used for months must not issue fifty requests to draw four numbers, and
    // under-reporting silently is worse than saying the figure is partial.
    vi.spyOn(auditApi, 'listLogs').mockResolvedValue(page(PAGE_SIZE, true) as never)

    const trail = await fetchAuditTrail()

    expect(trail.partial).toBe(true)
    expect(trail.logs.length).toBeGreaterThanOrEqual(MAX_ROWS)
  })

  it('survives a page that carries no rows at all', async () => {
    vi.spyOn(auditApi, 'listLogs').mockResolvedValue({
      data: { success: true, status: 'ok', message: '', code: 200, data: { logs: null, has_more: false } },
    } as never)

    await expect(fetchAuditTrail()).resolves.toEqual({ logs: [], partial: false })
  })
})
