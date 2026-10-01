/**
 * What the administrator dashboard should flag, derived from the summary counts.
 *
 * Kept apart from the component so the thresholds are visible and tested: a dashboard that
 * shows twenty healthy numbers and buries the one damaged file is worse than none.
 */

import type { AdminStats } from '@/api/admin_api'

export interface AttentionItem {
  /** Stable key for the list and for tests. */
  id: 'corrupted-files' | 'failed-checks' | 'pending-recovery' | 'audit-failures'
  severity: 'critical' | 'notice'
  message: string
}

const plural = (count: number, one: string, many = `${one}s`) => `${count} ${count === 1 ? one : many}`

export function attentionItems(stats: AdminStats): AttentionItem[] {
  const items: AttentionItem[] = []
  if (stats.files.corrupted > 0) {
    items.push({
      id: 'corrupted-files',
      severity: 'critical',
      message: `${plural(stats.files.corrupted, 'file')} failed the integrity check and is marked corrupted. Restore it from backup.`,
    })
  }
  if (stats.integrity.failed_checks_last_24_hours > 0) {
    items.push({
      id: 'failed-checks',
      severity: 'critical',
      message: `${plural(stats.integrity.failed_checks_last_24_hours, 'integrity check')} did not come back valid in the last 24 hours.`,
    })
  }
  if (stats.recovery.pending_requests > 0) {
    items.push({
      id: 'pending-recovery',
      severity: 'notice',
      message: `${plural(stats.recovery.pending_requests, 'recovery request')} awaiting review.`,
    })
  }
  if (stats.audit.failures_last_24_hours > 0) {
    items.push({
      id: 'audit-failures',
      severity: 'notice',
      message: `${plural(stats.audit.failures_last_24_hours, 'failed or blocked event')} in the last 24 hours.`,
    })
  }
  return items
}

/** "AES-256-GCM 9, ChaCha20-Poly1305 3", largest first, so the mix reads at a glance. */
export function algorithmMix(byAlgorithm: Record<string, number>): { name: string; count: number }[] {
  return Object.entries(byAlgorithm)
    .map(([name, count]) => ({ name, count }))
    .sort((a, b) => b.count - a.count || a.name.localeCompare(b.name))
}
