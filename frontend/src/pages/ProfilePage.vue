<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { BadgeCheck, MailWarning, Settings, ShieldCheck, Trash2, Upload } from 'lucide-vue-next'
import { RouterLink, useRouter } from 'vue-router'
import DeleteAccountDialog from '@/components/DeleteAccountDialog.vue'
import { avatarApi } from '@/api/avatar_api'
import { apiErrorMessage } from '@/api/http'
import { useAuthStore } from '@/stores/auth_store'

const router = useRouter()
const auth = useAuthStore()
const isLoading = ref(true)
const showDelete = ref(false)
const avatarBusy = ref(false)
const avatarMessage = ref('')
const avatarError = ref('')
const fileInput = ref<HTMLInputElement | null>(null)

/** Same locale rendering the file list and audit log use, so timestamps read alike. */
function formatTimestamp(value: string | null | undefined): string {
  if (!value) return 'Never'
  const parsed = new Date(value)
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString()
}

const details = computed(() => {
  const user = auth.user
  if (!user) return []
  return [
    { label: 'Username', value: user.username },
    { label: 'Email', value: user.email },
    { label: 'Role', value: user.role },
    { label: 'Account status', value: user.status },
    { label: 'Member since', value: formatTimestamp(user.created_at) },
    { label: 'Last sign-in', value: formatTimestamp(user.last_login_at) },
  ]
})

onMounted(async () => {
  // Forced: the menu may have cached this hours ago, and a profile page that shows a stale
  // status or sign-in time is worse than one that waits a moment.
  await auth.loadUser(true)
  isLoading.value = false
})

/**
 * The account is gone server-side; clear locally and send the user to register again.
 * Sessions were already revoked with the account.
 */
function onDeleted() {
  showDelete.value = false
  auth.clearLocalSession()
  router.push({ path: '/register', query: { deleted: '1' } })
}

function pickAvatar() {
  avatarError.value = ''
  avatarMessage.value = ''
  fileInput.value?.click()
}

async function onAvatarSelected(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return
  avatarBusy.value = true
  avatarError.value = ''
  avatarMessage.value = ''
  try {
    await avatarApi.upload(file)
    await auth.loadUser(true)
    avatarMessage.value = 'Profile picture updated'
  } catch (error) {
    avatarError.value = apiErrorMessage(error, 'Could not upload the picture')
  } finally {
    avatarBusy.value = false
  }
}

async function removeAvatar() {
  if (!auth.user?.has_avatar || avatarBusy.value) return
  avatarBusy.value = true
  avatarError.value = ''
  avatarMessage.value = ''
  try {
    await avatarApi.delete()
    await auth.loadUser(true)
    avatarMessage.value = 'Profile picture removed'
  } catch (error) {
    avatarError.value = apiErrorMessage(error, 'Could not remove the picture')
  } finally {
    avatarBusy.value = false
  }
}
</script>

<template>
  <section class="py-16 md:py-24">
    <div class="container mx-auto max-w-3xl px-4">
      <div class="rounded-xl border border-border bg-card p-6 md:p-8">
        <div class="flex flex-col items-start gap-5 sm:flex-row sm:items-center">
          <span
            class="flex h-20 w-20 shrink-0 items-center justify-center overflow-hidden rounded-full border border-border bg-primary/10 text-2xl font-bold text-primary"
          >
            <img
              v-if="auth.avatarUrl"
              :src="auth.avatarUrl"
              alt=""
              class="h-full w-full object-cover"
            />
            <template v-else>{{ auth.initials }}</template>
          </span>
          <div class="min-w-0">
            <h1 class="truncate text-2xl font-bold text-foreground md:text-3xl">
              {{ auth.displayName }}
            </h1>
            <p v-if="auth.user?.email" class="mt-1 truncate text-sm text-muted-foreground">
              {{ auth.user.email }}
            </p>
            <div class="mt-3 flex flex-wrap items-center gap-2">
              <span
                v-if="auth.user"
                class="inline-flex items-center gap-1.5 rounded-full bg-primary/10 px-2.5 py-1 text-xs font-medium text-primary"
              >
                <ShieldCheck class="h-3.5 w-3.5" />
                {{ auth.user.role }}
              </span>
              <span
                v-if="auth.user?.email_verified"
                class="inline-flex items-center gap-1.5 rounded-full bg-primary/10 px-2.5 py-1 text-xs font-medium text-primary"
              >
                <BadgeCheck class="h-3.5 w-3.5" />
                Email verified
              </span>
              <span
                v-else-if="auth.user"
                class="inline-flex items-center gap-1.5 rounded-full bg-destructive/10 px-2.5 py-1 text-xs font-medium text-destructive"
              >
                <MailWarning class="h-3.5 w-3.5" />
                Email not verified
              </span>
            </div>
          </div>
        </div>

        <div class="mt-6 flex flex-wrap items-center gap-2">
          <input
            ref="fileInput"
            type="file"
            accept="image/png,image/jpeg"
            class="hidden"
            @change="onAvatarSelected"
          />
          <button
            type="button"
            class="inline-flex h-10 items-center gap-2 rounded-md border border-border px-4 text-sm text-foreground transition-colors hover:bg-secondary disabled:opacity-50"
            :disabled="avatarBusy"
            @click="pickAvatar"
          >
            <Upload class="h-4 w-4" />
            {{ auth.user?.has_avatar ? 'Replace picture' : 'Upload picture' }}
          </button>
          <button
            v-if="auth.user?.has_avatar"
            type="button"
            class="inline-flex h-10 items-center gap-2 rounded-md border border-destructive/40 px-4 text-sm text-destructive transition-colors hover:bg-destructive/10 disabled:opacity-50"
            :disabled="avatarBusy"
            @click="removeAvatar"
          >
            <Trash2 class="h-4 w-4" />
            Remove picture
          </button>
        </div>
        <p class="mt-2 text-xs text-muted-foreground">
          PNG or JPEG, up to 512 KiB. Shown in the header and on this page.
        </p>
        <p v-if="avatarMessage" class="mt-2 text-sm text-primary">{{ avatarMessage }}</p>
        <p v-if="avatarError" class="mt-2 text-sm text-destructive">{{ avatarError }}</p>

        <p v-if="isLoading && !auth.user" class="mt-8 text-sm text-muted-foreground">
          Loading your account…
        </p>

        <p v-else-if="!auth.user" class="mt-8 text-sm text-muted-foreground">
          Your account details could not be loaded. The rest of the app still works; try
          refreshing this page.
        </p>

        <dl v-else class="mt-8 divide-y divide-border border-t border-border">
          <div
            v-for="item in details"
            :key="item.label"
            class="flex flex-wrap items-baseline justify-between gap-2 py-3"
          >
            <dt class="text-sm text-muted-foreground">{{ item.label }}</dt>
            <dd class="text-sm font-medium text-foreground">{{ item.value }}</dd>
          </div>
        </dl>

        <RouterLink
          to="/settings"
          class="mt-8 inline-flex h-10 items-center gap-2 rounded-md border border-border px-4 text-sm text-foreground transition-colors hover:bg-secondary"
        >
          <Settings class="h-4 w-4" />
          Account settings
        </RouterLink>
      </div>

      <div class="mt-6 rounded-xl border border-destructive/40 bg-card p-6 md:p-8">
        <h2 class="text-lg font-semibold text-foreground">Delete this account</h2>
        <p class="mt-2 max-w-2xl text-sm text-muted-foreground">
          Removes the account and every file uploaded from it. There is no way to reverse this
          and no way to recover the files afterwards. You will confirm with your login password
          and by typing DELETE — a single click is not enough.
        </p>
        <button
          type="button"
          class="mt-4 h-10 rounded-md border border-destructive/50 px-4 text-sm text-destructive transition-colors hover:bg-destructive/10"
          @click="showDelete = true"
        >
          Delete account
        </button>
      </div>
    </div>

    <DeleteAccountDialog v-if="showDelete" @deleted="onDeleted" @close="showDelete = false" />
  </section>
</template>
