<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { Loader2, RefreshCw, UserX, UserCheck } from 'lucide-vue-next'

import { adminApi, type AdminUserOut } from '@/api/admin_api'
import { apiErrorMessage } from '@/api/http'
import { unwrapData } from '@/api/types'
import { useAuthStore } from '@/stores/auth_store'

const auth = useAuthStore()
const users = ref<AdminUserOut[]>([])
const isLoading = ref(false)
const errorMessage = ref('')
const actionMessage = ref('')
const busyUserId = ref<string | null>(null)
const hasMore = ref(false)
const offset = ref(0)
const LIMIT = 50

function formatTimestamp(value: string | null): string {
  if (!value) return 'Never'
  const parsed = new Date(value)
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString()
}

async function load(reset = true) {
  isLoading.value = true
  errorMessage.value = ''
  if (reset) offset.value = 0
  try {
    const data = unwrapData(await adminApi.listUsers({ limit: LIMIT, offset: offset.value }))
    users.value = reset ? data.users : [...users.value, ...data.users]
    hasMore.value = data.has_more
  } catch (error) {
    errorMessage.value = apiErrorMessage(error, 'Failed to load users')
  } finally {
    isLoading.value = false
  }
}

async function loadMore() {
  offset.value += LIMIT
  await load(false)
}

async function setEnabled(user: AdminUserOut, enabled: boolean) {
  if (user.user_id === auth.user?.id) {
    actionMessage.value = 'You cannot disable your own account from this panel.'
    return
  }
  busyUserId.value = user.user_id
  actionMessage.value = ''
  errorMessage.value = ''
  try {
    const data = unwrapData(
      await (enabled ? adminApi.enableUser(user.user_id) : adminApi.disableUser(user.user_id)),
    )
    user.status = data.status
    actionMessage.value = enabled
      ? `Enabled ${user.username}.`
      : `Disabled ${user.username}; revoked ${data.revoked_sessions} session(s).`
  } catch (error) {
    errorMessage.value = apiErrorMessage(error, `Could not update ${user.username}`)
  } finally {
    busyUserId.value = null
  }
}

onMounted(() => {
  void load()
})
</script>

<template>
  <div>
    <div class="mb-4 flex flex-wrap items-center justify-between gap-3">
      <div>
        <h2 class="text-lg font-semibold text-foreground">Users</h2>
        <p class="text-sm text-muted-foreground">Enable or disable accounts. Disabling revokes every active session.</p>
      </div>
      <button
        type="button"
        class="inline-flex h-9 items-center gap-2 rounded-md border border-border px-3 text-sm hover:bg-secondary"
        :disabled="isLoading"
        @click="load()"
      >
        <RefreshCw class="h-4 w-4" :class="{ 'animate-spin': isLoading }" />
        Refresh
      </button>
    </div>

    <p v-if="actionMessage" class="mb-3 text-sm text-muted-foreground">{{ actionMessage }}</p>
    <p v-if="errorMessage" class="mb-3 text-sm text-destructive" role="alert">{{ errorMessage }}</p>

    <div v-if="isLoading && !users.length" class="py-10 text-center text-sm text-muted-foreground">
      Loading users…
    </div>
    <div v-else-if="!users.length" class="py-10 text-center text-sm text-muted-foreground">
      No users found.
    </div>
    <div v-else class="overflow-x-auto rounded-xl border border-border">
      <table class="w-full min-w-[40rem] text-left text-sm">
        <thead class="border-b border-border bg-secondary/40 text-xs uppercase tracking-wide text-muted-foreground">
          <tr>
            <th class="px-4 py-3 font-medium">Username</th>
            <th class="px-4 py-3 font-medium">Role</th>
            <th class="px-4 py-3 font-medium">Status</th>
            <th class="px-4 py-3 font-medium">Last sign-in</th>
            <th class="px-4 py-3 font-medium text-right">Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="user in users"
            :key="user.user_id"
            class="border-b border-border last:border-0"
          >
            <td class="px-4 py-3 font-medium text-foreground">{{ user.username }}</td>
            <td class="px-4 py-3 text-muted-foreground">{{ user.role }}</td>
            <td class="px-4 py-3">
              <span
                class="rounded-full px-2 py-0.5 text-xs font-medium"
                :class="
                  user.status === 'ACTIVE'
                    ? 'bg-primary/10 text-primary'
                    : 'bg-destructive/10 text-destructive'
                "
              >
                {{ user.status }}
              </span>
            </td>
            <td class="px-4 py-3 text-muted-foreground">{{ formatTimestamp(user.last_login_at) }}</td>
            <td class="px-4 py-3 text-right">
              <button
                v-if="user.status === 'ACTIVE'"
                type="button"
                class="inline-flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs text-destructive hover:bg-destructive/10 disabled:opacity-50"
                :disabled="busyUserId === user.user_id"
                @click="setEnabled(user, false)"
              >
                <Loader2 v-if="busyUserId === user.user_id" class="h-3.5 w-3.5 animate-spin" />
                <UserX v-else class="h-3.5 w-3.5" />
                Disable
              </button>
              <button
                v-else
                type="button"
                class="inline-flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs text-primary hover:bg-primary/10 disabled:opacity-50"
                :disabled="busyUserId === user.user_id"
                @click="setEnabled(user, true)"
              >
                <Loader2 v-if="busyUserId === user.user_id" class="h-3.5 w-3.5 animate-spin" />
                <UserCheck v-else class="h-3.5 w-3.5" />
                Enable
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="hasMore" class="mt-4 text-center">
      <button
        type="button"
        class="h-9 rounded-md border border-border px-4 text-sm hover:bg-secondary disabled:opacity-50"
        :disabled="isLoading"
        @click="loadMore"
      >
        Load more
      </button>
    </div>
  </div>
</template>
