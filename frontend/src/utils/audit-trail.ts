import { auditApi, type AuditLogFilters } from '@/api/audit_api'
import { unwrapData, type AuditLogOut } from '@/api/types'

/** The server caps a page at 100. */
export const PAGE_SIZE = 100

export type AuditResultFilter = '' | 'SUCCESS' | 'FAIL'

/**
 * What the filter bar holds, as the form controls hold it: strings, empty when unset.
 *
 * `from` and `to` are `YYYY-MM-DD` from a date input, in the person's local calendar. They
 * become UTC instants only when the request is built, see `toAuditLogFilters`.
 */
export interface AuditFilterForm {
  action: string
  result: AuditResultFilter
  from: string
  to: string
  q: string
}

export const EMPTY_AUDIT_FILTERS: Readonly<AuditFilterForm> = Object.freeze({
  action: '',
  result: '',
  from: '',
  to: '',
  q: '',
})

export function hasAuditFilters(form: AuditFilterForm): boolean {
  return Object.values(form).some((value) => value.trim() !== '')
}

/** A local calendar day, or null when the input is not a complete `YYYY-MM-DD`. */
function localDay(value: string): [number, number, number] | null {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value.trim())
  if (!match) return null
  const [year, month, day] = [Number(match[1]), Number(match[2]), Number(match[3])]
  const probe = new Date(year, month - 1, day)
  if (probe.getFullYear() !== year || probe.getMonth() !== month - 1 || probe.getDate() !== day) {
    return null
  }
  return [year, month, day]
}

/**
 * The request the server reads, from what the form holds.
 *
 * A date picked in Melbourne means that whole day in Melbourne: `from` is its first instant
 * and `to` its last, both converted to UTC, so the window the person sees on screen is the
 * window the server applies. Blank fields are left out entirely.
 */
export function toAuditLogFilters(form: AuditFilterForm): AuditLogFilters {
  const filters: AuditLogFilters = {}
  if (form.action) filters.action = form.action
  if (form.result === 'SUCCESS' || form.result === 'FAIL') filters.result = form.result
  const from = localDay(form.from)
  if (from) filters.from = new Date(from[0], from[1] - 1, from[2], 0, 0, 0, 0).toISOString()
  const to = localDay(form.to)
  if (to) filters.to = new Date(to[0], to[1] - 1, to[2], 23, 59, 59, 999).toISOString()
  const keyword = form.q.trim()
  if (keyword) filters.q = keyword.slice(0, 100)
  return filters
}

export interface AuditPage {
  logs: AuditLogOut[]
  /** The server has rows after these; `offset + logs.length` asks for them. */
  hasMore: boolean
}

/**
 * One page of the trail, newest first.
 *
 * The page used to walk every page up front, a thousand rows and ten requests on a long-lived
 * account, so that four stat cards could be totals of everything. It now loads one page, shows
 * it, and loads the next only when asked; the stat cards say they cover what is loaded.
 */
export async function fetchAuditPage(filters: AuditLogFilters, offset: number): Promise<AuditPage> {
  const page = unwrapData(await auditApi.listLogs({ ...filters, limit: PAGE_SIZE, offset }))
  return { logs: page?.logs ?? [], hasMore: page?.has_more === true }
}
