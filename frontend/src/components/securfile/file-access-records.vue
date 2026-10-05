<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import PageHeader from '@/components/securfile/PageHeader.vue'
import { Activity, AlertTriangle, ChevronDown, ChevronUp, Clock, Download, FileIcon, RefreshCw, Share2, User } from 'lucide-vue-next'
import { auditApi } from '@/api/audit_api'
import { formatFileSize, unwrapData, type AuditLogOut } from '@/api/types'
import {
  auditActionLabel,
  auditSubjectFileId,
  isDownloadAction,
  isShareAction,
} from '@/utils/audit-actions'
import { fetchAuditTrail } from '@/utils/audit-trail'
import { fallbackFileLabel, resolveFileNames } from '@/utils/file-names'

interface AccessEvent {
  id: string
  /** Who did it. The API sends the username; only an admin ever sees anyone else's. */
  actor: string
  accessTime: string
  /** Human label, e.g. "Downloaded". */
  action: string
  isDownload: boolean
  /** Sharing or revoking -- an action that changed who can reach the file. */
  isShare: boolean
  /** SUCCESS, or the failure this row records. */
  succeeded: boolean
  /** "Shared with junyan", the size uploaded -- whatever this action has worth saying. */
  detail: string
}

interface AuditGroup {
  id: string
  name: string
  /** Account-level rows (sign-in, key changes) belong to no file and say so. */
  isAccount: boolean
  sharedAt: string
  totalDownloads: number
  totalShares: number
  accessHistory: AccessEvent[]
}

interface StatCard {
  key: 'totalFiles' | 'totalDownloads' | 'totalShares' | 'uniqueUsers'
  label: string
  icon: typeof FileIcon
  wrapperClass: string
  iconClass: string
}

const logs = ref<AuditLogOut[]>([])
const isLoading = ref(false)
const errorMessage = ref('')
const expanded = ref<string[]>([])
const chainState = ref<'unknown' | 'valid' | 'invalid' | 'unavailable'>('unknown')
const chainCheckedEntries = ref(0)
const fileNames = ref<Map<string, string>>(new Map())

const ACCOUNT_GROUP = 'account'

/** Same locale rendering the file list uses, so timestamps read alike across the app. */
const formatTimestamp = (value: string | null | undefined): string => {
  if (!value) return '-'
  const parsed = new Date(value)
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString()
}

/** Whatever this particular action has worth saying beyond its name. */
const detailOf = (log: AuditLogOut): string => {
  if (log.target_username) return `with ${log.target_username}`
  if (log.description) return log.description
  const size = log.metadata?.ciphertext_size
  return typeof size === 'number' ? formatFileSize(size) : ''
}

const mapLogToEvent = (log: AuditLogOut, index: number): AccessEvent => ({
  id: `${log.created_at}-${log.action}-${index}`,
  actor: log.actor_username ?? 'A deleted account',
  accessTime: formatTimestamp(log.created_at),
  action: auditActionLabel(log.action),
  isDownload: isDownloadAction(log.action),
  isShare: isShareAction(log.action),
  succeeded: log.result === 'SUCCESS',
  detail: detailOf(log),
})

const groups = computed<AuditGroup[]>(() => {
  const grouped = new Map<string, AuditGroup>()
  for (const [index, log] of logs.value.entries()) {
    // Signing in, changing a passphrase and closing an account are about the account, not
    // about any file. They used to fall into a single group labelled with a file id they
    // never had; they get their own heading now.
    const fileId = auditSubjectFileId(log)
    const key = fileId ?? ACCOUNT_GROUP
    const event = mapLogToEvent(log, index)
    const existing = grouped.get(key)
    if (existing) {
      existing.accessHistory.push(event)
      if (event.isDownload) existing.totalDownloads += 1
      if (event.isShare) existing.totalShares += 1
    } else {
      grouped.set(key, {
        id: key,
        name: fileId
          ? (fileNames.value.get(fileId) ?? fallbackFileLabel(fileId))
          : 'Account activity',
        isAccount: fileId === null,
        sharedAt: formatTimestamp(log.created_at),
        totalDownloads: event.isDownload ? 1 : 0,
        totalShares: event.isShare ? 1 : 0,
        accessHistory: [event],
      })
    }
  }
  // Files first; the account group is context, not the subject of the page.
  return Array.from(grouped.values()).sort(
    (a, b) => Number(a.isAccount) - Number(b.isAccount),
  )
})

const stats = computed(() => ({
  totalFiles: groups.value.filter((group) => !group.isAccount).length,
  totalDownloads: groups.value.reduce((sum, f) => sum + f.totalDownloads, 0),
  totalShares: groups.value.reduce((sum, f) => sum + f.totalShares, 0),
  // Was counting row ids, so it only ever restated the number of log entries.
  uniqueUsers: new Set(groups.value.flatMap((f) => f.accessHistory.map((u) => u.actor))).size,
}))

const statCards: StatCard[] = [
  { key: 'totalFiles', label: 'Tracked Files', icon: FileIcon, wrapperClass: 'bg-secondary', iconClass: 'text-foreground' },
  { key: 'totalDownloads', label: 'Downloads', icon: Download, wrapperClass: 'bg-secondary', iconClass: 'text-foreground' },
  { key: 'totalShares', label: 'Shares', icon: Share2, wrapperClass: 'bg-secondary', iconClass: 'text-foreground' },
  { key: 'uniqueUsers', label: 'Unique Users', icon: User, wrapperClass: 'bg-secondary', iconClass: 'text-foreground' },
]

const trailIsPartial = ref(false)

const loadLogs = async () => {
  isLoading.value = true
  errorMessage.value = ''
  try {
    const trail = await fetchAuditTrail()
    logs.value = trail.logs
    trailIsPartial.value = trail.partial

    // The audit response carries file_id and no filename, so the names are resolved here.
    // Deliberately after the rows are on screen and not awaited into the loading state: the
    // history is readable without them, and a slow lookup should not hold it back.
    const ids = logs.value
      .map(auditSubjectFileId)
      .filter((id): id is string => id !== null)
    resolveFileNames(ids)
      .then((names) => {
        fileNames.value = names
      })
      .catch(() => {
        // Labels stay as ids. Not worth an error banner over the history itself loading.
      })
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Failed to load audit logs'
  } finally {
    isLoading.value = false
  }
}

/**
 * Verify the tamper-evident chain, when the caller is allowed to.
 *
 * `POST /audit-logs/verify-chain` is ADMIN-only and recomputes every hash in the table, so
 * restricting it is right. The page called it for everyone and printed the refusal as red
 * text, which meant an ordinary user opening their own history was met with what looked like
 * a broken audit log. Not being permitted to run the check is not a finding: the line is
 * hidden instead.
 *
 * An actual INVALID result is the opposite -- it is the single most important thing this
 * page can say -- so it is kept distinct from both.
 */
const verifyChain = async () => {
  try {
    const data = unwrapData(await auditApi.verifyChain())
    chainState.value = data.valid ? 'valid' : 'invalid'
    chainCheckedEntries.value = data.checked_entries ?? 0
  } catch {
    chainState.value = 'unavailable'
  }
}

onMounted(() => {
  loadLogs()
  verifyChain()
})

const toggle = (id: string) => {
  expanded.value = expanded.value.includes(id)
    ? expanded.value.filter((x) => x !== id)
    : [...expanded.value, id]
}
</script>

<template>
  <section id="access-records" class="product-page">
    <div class="page-container">
      <PageHeader title="File Access Records" subtitle="Track security-sensitive actions recorded by the audit log service">
        <template #actions>
          <button class="h-10 px-4 inline-flex items-center gap-2 rounded-md border border-border bg-card hover:bg-secondary" @click="loadLogs">
            <RefreshCw class="h-4 w-4" :class="{ 'animate-spin': isLoading }" />
            Refresh
          </button>
          <span v-if="chainState === 'valid'" class="inline-flex items-center gap-1.5 rounded-md bg-success-soft px-2.5 py-1 font-mono text-xs text-success">
            <span aria-hidden="true">●</span>
            Hash chain verified · {{ chainCheckedEntries }} entries
          </span>
          <span
            v-else-if="chainState === 'invalid'"
            class="text-sm font-medium text-destructive inline-flex items-center gap-1"
          >
            <AlertTriangle class="h-4 w-4" />
            Hash chain broken — this log has been altered
          </span>
        </template>
      </PageHeader>

      <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <div v-for="card in statCards" :key="card.key" class="bg-card border border-border rounded-xl p-4">
          <div class="flex items-center gap-3">
            <div class="p-2 rounded-lg" :class="card.wrapperClass">
              <component :is="card.icon" class="h-5 w-5" :class="card.iconClass" />
            </div>
            <div>
              <p class="text-2xl font-semibold tracking-tight text-foreground">{{ stats[card.key] }}</p>
              <p class="text-xs text-muted-foreground">{{ card.label }}</p>
            </div>
          </div>
        </div>
      </div>

      <p v-if="errorMessage" class="text-center text-sm text-destructive mb-4">{{ errorMessage }}</p>
      <p v-if="groups.length" class="mb-4 flex items-center gap-2 text-sm text-muted-foreground" data-testid="records-hint">
        <ChevronDown class="h-4 w-4 shrink-0" />
        Select a file below to open its full access history: who uploaded, shared or downloaded it, and when.
      </p>
      <p v-if="trailIsPartial" class="text-center text-xs text-muted-foreground mb-4">
        Showing the most recent {{ logs.length }} events; totals cover these only.
      </p>

      <div v-if="isLoading && !groups.length" class="text-center py-12 text-muted-foreground">
        Loading audit logs...
      </div>

      <div v-else-if="!groups.length" class="text-center py-12 text-muted-foreground max-w-xl mx-auto">
        No audit logs yet. Actions such as upload, download, and share will appear here.
      </div>

      <div v-else class="space-y-3">
        <article v-for="file in groups" :key="file.id" class="bg-card border border-border rounded-xl overflow-hidden">
          <button
            class="w-full p-4 text-left hover:bg-secondary/40 transition-colors"
            :aria-expanded="expanded.includes(file.id)"
            @click="toggle(file.id)"
          >
            <div class="flex items-center justify-between gap-4">
              <div class="flex items-center gap-4">
                <div class="p-3 rounded-lg bg-secondary">
                  <User v-if="file.isAccount" class="h-5 w-5 text-muted-foreground" />
                  <FileIcon v-else class="h-5 w-5 text-muted-foreground" />
                </div>
                <div>
                  <h3 translate="no" class="text-base text-foreground">{{ file.name }}</h3>
                  <p class="text-sm text-muted-foreground flex items-center gap-2 mt-1"><Clock class="h-3 w-3" /> Last activity {{ file.sharedAt }}</p>
                </div>
              </div>
              <div class="flex shrink-0 items-center gap-4 text-sm text-muted-foreground">
                <span class="hidden items-center gap-1 md:inline-flex" title="Downloads"><Download class="h-4 w-4" /> {{ file.totalDownloads }}</span>
                <span class="hidden items-center gap-1 md:inline-flex" title="People involved"><User class="h-4 w-4" /> {{ new Set(file.accessHistory.map((e) => e.actor)).size }}</span>
                <span class="inline-flex items-center gap-1 text-xs font-medium text-foreground" data-testid="records-toggle">
                  <span class="hidden sm:inline">{{ expanded.includes(file.id) ? 'Hide history' : 'View history' }}</span>
                  <component :is="expanded.includes(file.id) ? ChevronUp : ChevronDown" class="h-4 w-4" />
                </span>
              </div>
            </div>
          </button>

          <div v-if="expanded.includes(file.id)" class="border-t border-border p-4">
            <div class="flex items-center gap-2 text-sm text-muted-foreground mb-4"><Activity class="h-4 w-4" /><span>Recent Access History</span></div>
            <div class="space-y-3">
              <div
                v-for="event in file.accessHistory"
                :key="event.id"
                class="flex items-start justify-between gap-4 p-3 rounded-lg bg-secondary/50"
              >
                <div class="min-w-0">
                  <p class="text-sm font-medium text-foreground">
                    {{ event.action }}
                    <span v-if="event.detail" class="font-normal text-muted-foreground">
                      {{ event.detail }}
                    </span>
                  </p>
                  <p translate="no" class="mt-0.5 font-mono text-xs text-muted-foreground">
                    {{ event.actor }} · {{ event.accessTime }}
                  </p>
                </div>
                <span
                  v-if="!event.succeeded"
                  class="shrink-0 rounded-md bg-destructive-soft px-2 py-0.5 text-xs text-destructive"
                >
                  Failed
                </span>
              </div>
            </div>
          </div>
        </article>
      </div>
    </div>
  </section>
</template>
