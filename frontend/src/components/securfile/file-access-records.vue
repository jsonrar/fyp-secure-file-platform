<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Activity, Clock, Download, Eye, FileIcon, RefreshCw, User } from 'lucide-vue-next'
import { auditApi } from '@/api/audit_api'
import { unwrapData, type AuditLogOut } from '@/api/types'

interface AccessUser {
  id: string
  name: string
  accessTime: string
  action: string
  device: string
  location: string
}

interface AuditGroup {
  id: string
  name: string
  sharedAt: string
  totalViews: number
  totalDownloads: number
  accessHistory: AccessUser[]
}

interface StatCard {
  key: 'totalFiles' | 'totalViews' | 'totalDownloads' | 'uniqueUsers'
  label: string
  icon: typeof FileIcon
  wrapperClass: string
  iconClass: string
}

const logs = ref<AuditLogOut[]>([])
const isLoading = ref(false)
const errorMessage = ref('')
const expanded = ref<string[]>([])
const chainStatus = ref('')

const mapLogToUser = (log: AuditLogOut, index: number): AccessUser => ({
  id: String(log.log_id ?? index),
  name: log.actor_username ?? 'Unknown user',
  accessTime: log.created_at ?? '-',
  action: log.action ?? 'view',
  device: log.device ?? 'Unknown device',
  location: log.location ?? 'Unknown',
})

const groups = computed<AuditGroup[]>(() => {
  const grouped = new Map<string, AuditGroup>()
  for (const [index, log] of logs.value.entries()) {
    const fileId = String(log.file_id ?? 'unknown')
    const existing = grouped.get(fileId)
    const user = mapLogToUser(log, index)
    if (existing) {
      existing.accessHistory.push(user)
      if (user.action === 'download') existing.totalDownloads += 1
      else existing.totalViews += 1
    } else {
      grouped.set(fileId, {
        id: fileId,
        name: `File #${fileId}`,
        sharedAt: log.created_at ?? '-',
        totalViews: user.action === 'download' ? 0 : 1,
        totalDownloads: user.action === 'download' ? 1 : 0,
        accessHistory: [user],
      })
    }
  }
  return Array.from(grouped.values())
})

const stats = computed(() => ({
  totalFiles: groups.value.length,
  totalViews: groups.value.reduce((sum, f) => sum + f.totalViews, 0),
  totalDownloads: groups.value.reduce((sum, f) => sum + f.totalDownloads, 0),
  uniqueUsers: new Set(groups.value.flatMap((f) => f.accessHistory.map((u) => u.id))).size,
}))

const statCards: StatCard[] = [
  { key: 'totalFiles', label: 'Tracked Files', icon: FileIcon, wrapperClass: 'bg-primary/10', iconClass: 'text-primary' },
  { key: 'totalViews', label: 'Total Views', icon: Eye, wrapperClass: 'bg-blue-500/10', iconClass: 'text-blue-500' },
  { key: 'totalDownloads', label: 'Downloads', icon: Download, wrapperClass: 'bg-primary/10', iconClass: 'text-primary' },
  { key: 'uniqueUsers', label: 'Unique Users', icon: User, wrapperClass: 'bg-amber-500/10', iconClass: 'text-amber-500' },
]

const loadLogs = async () => {
  isLoading.value = true
  errorMessage.value = ''
  try {
    const res = await auditApi.listLogs()
    const data = unwrapData(res)
    logs.value = data.logs ?? []
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Failed to load audit logs'
  } finally {
    isLoading.value = false
  }
}

const verifyChain = async () => {
  try {
    const res = await auditApi.verifyChain()
    const data = unwrapData(res)
    chainStatus.value = data.status ?? 'UNKNOWN'
  } catch (error) {
    chainStatus.value = error instanceof Error ? error.message : 'Verification failed'
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
  <section id="access-records" class="py-20 bg-background">
    <div class="container mx-auto px-4">
      <div class="text-center mb-16">
        <h2 class="text-3xl md:text-4xl font-bold text-foreground mb-4">File Access Records</h2>
        <p class="text-muted-foreground max-w-2xl mx-auto text-pretty">Track security-sensitive actions recorded by the audit log service</p>
      </div>

      <div class="flex items-center justify-center gap-3 mb-8">
        <button class="h-10 px-4 inline-flex items-center gap-2 rounded-md border border-border hover:bg-secondary" @click="loadLogs">
          <RefreshCw class="h-4 w-4" :class="{ 'animate-spin': isLoading }" />
          Refresh
        </button>
        <span v-if="chainStatus" class="text-sm text-muted-foreground">Hash chain: {{ chainStatus }}</span>
      </div>

      <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8 max-w-4xl mx-auto">
        <div v-for="card in statCards" :key="card.key" class="bg-card border border-border rounded-xl p-4">
          <div class="flex items-center gap-3">
            <div class="p-2 rounded-lg" :class="card.wrapperClass">
              <component :is="card.icon" class="h-5 w-5" :class="card.iconClass" />
            </div>
            <div>
              <p class="text-2xl font-bold text-foreground">{{ stats[card.key] }}</p>
              <p class="text-xs text-muted-foreground">{{ card.label }}</p>
            </div>
          </div>
        </div>
      </div>

      <p v-if="errorMessage" class="text-center text-sm text-destructive mb-4">{{ errorMessage }}</p>

      <div v-if="isLoading && !groups.length" class="text-center py-12 text-muted-foreground">
        Loading audit logs...
      </div>

      <div v-else-if="!groups.length" class="text-center py-12 text-muted-foreground max-w-xl mx-auto">
        No audit logs yet. Actions such as upload, download, and share will appear here.
      </div>

      <div v-else class="max-w-4xl mx-auto space-y-4">
        <article v-for="file in groups" :key="file.id" class="bg-card border border-border rounded-xl overflow-hidden">
          <button class="w-full p-4 text-left hover:bg-secondary/40 transition-colors" @click="toggle(file.id)">
            <div class="flex items-center justify-between gap-4">
              <div class="flex items-center gap-4">
                <div class="p-3 rounded-lg bg-secondary"><FileIcon class="h-5 w-5 text-primary" /></div>
                <div>
                  <h3 class="text-base text-foreground">{{ file.name }}</h3>
                  <p class="text-sm text-muted-foreground flex items-center gap-2 mt-1"><Clock class="h-3 w-3" /> Last activity {{ file.sharedAt }}</p>
                </div>
              </div>
              <div class="hidden md:flex items-center gap-4 text-sm text-muted-foreground">
                <span class="inline-flex items-center gap-1"><Eye class="h-4 w-4" /> {{ file.totalViews }}</span>
                <span class="inline-flex items-center gap-1"><Download class="h-4 w-4" /> {{ file.totalDownloads }}</span>
              </div>
            </div>
          </button>

          <div v-if="expanded.includes(file.id)" class="border-t border-border p-4">
            <div class="flex items-center gap-2 text-sm text-muted-foreground mb-4"><Activity class="h-4 w-4" /><span>Recent Access History</span></div>
            <div class="space-y-3">
              <div v-for="user in file.accessHistory" :key="user.id" class="flex items-center justify-between p-3 rounded-lg bg-secondary/50">
                <div>
                  <p class="text-sm font-medium text-foreground">{{ user.name }}</p>
                  <p class="text-xs text-muted-foreground">{{ user.accessTime }} · {{ user.action }}</p>
                </div>
                <div class="text-right">
                  <p class="text-xs text-muted-foreground">{{ user.device }}</p>
                  <p class="text-xs text-muted-foreground">{{ user.location }}</p>
                </div>
              </div>
            </div>
          </div>
        </article>
      </div>
    </div>
  </section>
</template>
