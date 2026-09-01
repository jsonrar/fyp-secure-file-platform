import { auditApi } from '@/api/audit_api'
import { unwrapData, type AuditLogOut } from '@/api/types'

/** The server caps a page at 100. */
export const PAGE_SIZE = 100

/**
 * Stop after this many rows even if more remain.
 *
 * A bound is necessary -- an account used for months should not issue fifty requests to
 * draw four numbers -- and the caller is told when it was reached, so the page can say the
 * totals are partial instead of quietly under-reporting.
 */
export const MAX_ROWS = 1000

export interface AuditTrail {
  logs: AuditLogOut[]
  /** True when MAX_ROWS stopped the walk before the server ran out of rows. */
  partial: boolean
}

/**
 * Every page of the caller's trail, not just the first.
 *
 * The stat cards summarise this. Reading only the first page made them totals of the last
 * fifty events while looking like totals of everything: on a test account holding 83 rows,
 * the first page showed four distinct files, twelve downloads and eight shares, against a
 * true eight, nineteen and thirteen. Sign-ins made it worse -- 22 of those 50 rows were
 * logins, crowding out the file activity the page exists to show.
 */
export async function fetchAuditTrail(): Promise<AuditTrail> {
  const logs: AuditLogOut[] = []
  let offset = 0

  for (;;) {
    const page = unwrapData(await auditApi.listLogs({ limit: PAGE_SIZE, offset }))
    logs.push(...(page?.logs ?? []))

    if (!page?.has_more) return { logs, partial: false }
    if (logs.length >= MAX_ROWS) return { logs, partial: true }
    offset += PAGE_SIZE
  }
}
