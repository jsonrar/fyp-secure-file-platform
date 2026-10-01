<script setup lang="ts">
import { computed, onMounted, ref, type Component } from 'vue'
import { Bot, FileIcon, KeyRound, LayoutDashboard, LifeBuoy, ScanSearch, ShieldCheck, Users } from 'lucide-vue-next'
import { RouterLink } from 'vue-router'

import AdminAgentPanel from '@/components/admin/AdminAgentPanel.vue'
import AdminAuditPanel from '@/components/admin/AdminAuditPanel.vue'
import AdminFilesPanel from '@/components/admin/AdminFilesPanel.vue'
import AdminIntegrityPanel from '@/components/admin/AdminIntegrityPanel.vue'
import AdminRecoveryKeyPanel from '@/components/admin/AdminRecoveryKeyPanel.vue'
import AdminStatsPanel from '@/components/admin/AdminStatsPanel.vue'
import AdminRecoveryRequestsPanel from '@/components/admin/AdminRecoveryRequestsPanel.vue'
import AdminUsersPanel from '@/components/admin/AdminUsersPanel.vue'
import { useAuthStore } from '@/stores/auth_store'

type TabId =
  | 'overview'
  | 'recovery'
  | 'users'
  | 'files'
  | 'integrity'
  | 'agent'
  | 'audit'
  | 'recovery-key'

interface Tab {
  id: TabId
  label: string
  icon: typeof Users
  adminOnly: boolean
}

const auth = useAuthStore()
const ready = ref(false)
const activeTab = ref<TabId>('recovery')

const tabs = computed<Tab[]>(() => {
  const all: Tab[] = [
    { id: 'overview', label: 'Overview', icon: LayoutDashboard, adminOnly: true },
    { id: 'recovery', label: 'Recovery requests', icon: LifeBuoy, adminOnly: false },
    { id: 'users', label: 'Users', icon: Users, adminOnly: true },
    { id: 'files', label: 'Files', icon: FileIcon, adminOnly: true },
    { id: 'integrity', label: 'Integrity', icon: ScanSearch, adminOnly: true },
    { id: 'agent', label: 'Security agent', icon: Bot, adminOnly: true },
    { id: 'audit', label: 'Audit chain', icon: ShieldCheck, adminOnly: true },
    { id: 'recovery-key', label: 'Recovery key', icon: KeyRound, adminOnly: true },
  ]
  if (auth.isAdmin) return all
  return all.filter((tab) => !tab.adminOnly)
})

const panelMap: Record<TabId, Component> = {
  overview: AdminStatsPanel,
  recovery: AdminRecoveryRequestsPanel,
  users: AdminUsersPanel,
  files: AdminFilesPanel,
  integrity: AdminIntegrityPanel,
  agent: AdminAgentPanel,
  audit: AdminAuditPanel,
  'recovery-key': AdminRecoveryKeyPanel,
}

const activePanel = computed(() => panelMap[activeTab.value])

const roleLabel = computed(() => {
  if (auth.isAdmin) return 'Administrator'
  if (auth.user?.role === 'RECOVERY_OFFICER') return 'Recovery officer'
  return auth.user?.role ?? 'Signed-in user'
})

onMounted(async () => {
  await auth.loadUser(true)
  ready.value = true
  // An administrator lands on the overview; a recovery officer, who cannot read it, on the queue.
  activeTab.value = auth.isAdmin ? 'overview' : 'recovery'
})
</script>

<template>
  <section class="py-16 md:py-20">
    <div class="container mx-auto max-w-5xl px-4">
      <div class="mb-10 text-center">
        <h1 class="text-3xl font-bold text-foreground md:text-4xl">Operations</h1>
        <p class="mx-auto mt-3 max-w-2xl text-muted-foreground">
          Role-aware administration, recovery review, and audit-chain verification using the
          existing backend APIs.
        </p>
      </div>

      <div v-if="!ready" class="py-16 text-center text-sm text-muted-foreground">
        Loading account…
      </div>

      <div
        v-else-if="!auth.isRecoveryReviewer && auth.user"
        class="mx-auto max-w-2xl"
      >
        <div class="rounded-xl border border-border bg-card p-6">
          <h2 class="text-lg font-semibold text-foreground">Your recovery requests</h2>
          <p class="mt-2 text-sm text-muted-foreground">
            You are signed in as a {{ roleLabel }}. User and platform administration require
            <span class="font-medium text-foreground">ADMIN</span> or
            <span class="font-medium text-foreground">RECOVERY_OFFICER</span>. You can still open
            recovery requests for files you can access from
            <RouterLink to="/files" class="text-primary underline-offset-2 hover:underline">My Files</RouterLink>,
            and track them below.
          </p>
        </div>
        <div class="mt-8">
          <AdminRecoveryRequestsPanel :can-review="false" />
        </div>
      </div>

      <div v-else-if="auth.isRecoveryReviewer">
        <p class="mb-6 text-center text-sm text-muted-foreground">
          Signed in as <span class="font-medium text-foreground">{{ roleLabel }}</span>
          ({{ auth.displayName }})
        </p>

        <div
          class="mb-8 flex flex-wrap justify-center gap-2 border-b border-border pb-4"
          role="tablist"
          aria-label="Operations sections"
        >
          <button
            v-for="tab in tabs"
            :key="tab.id"
            type="button"
            role="tab"
            :aria-selected="activeTab === tab.id"
            class="inline-flex items-center gap-2 rounded-md px-3 py-2 text-sm transition-colors"
            :class="
              activeTab === tab.id
                ? 'bg-primary/10 font-medium text-primary'
                : 'text-muted-foreground hover:bg-secondary hover:text-foreground'
            "
            @click="activeTab = tab.id"
          >
            <component :is="tab.icon" class="h-4 w-4" />
            {{ tab.label }}
          </button>
        </div>

        <div role="tabpanel">
          <AdminRecoveryRequestsPanel
            v-if="activeTab === 'recovery'"
            :can-review="true"
          />
          <component :is="activePanel" v-else />
        </div>
      </div>

      <div v-else class="py-16 text-center text-sm text-muted-foreground">
        Could not load your account role. Try refreshing, or
        <RouterLink to="/login" class="text-primary underline-offset-2 hover:underline">sign in</RouterLink>
        again.
      </div>
    </div>
  </section>
</template>
