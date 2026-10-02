<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import {
  BadgeCheck,
  Camera,
  Loader2,
  MailWarning,
  Settings,
  ShieldCheck,
  Trash2,
} from 'lucide-vue-next'
import { RouterLink, useRouter } from 'vue-router'
import DeleteAccountDialog from '@/components/DeleteAccountDialog.vue'
import { apiErrorMessage } from '@/api/http'
import { useAuthStore } from '@/stores/auth_store'

const router = useRouter()
const auth = useAuthStore()
const isLoading = ref(true)
const showDelete = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)
const avatarBusy = ref(false)
const avatarError = ref('')
const avatarMessage = ref('')

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

function openFilePicker() {
  avatarError.value = ''
  avatarMessage.value = ''
  fileInput.value?.click()
}

async function onAvatarSelected(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return

  if (!['image/png', 'image/jpeg'].includes(file.type)) {
    avatarError.value = 'Choose a PNG or JPEG image.'
    return
  }
  if (file.size > 512 * 1024) {
    avatarError.value = 'Avatar must be 512 KB or smaller.'
    return
  }

  avatarBusy.value = true
  avatarError.value = ''
  avatarMessage.value = ''
  try {
    await auth.uploadAvatar(file)
    avatarMessage.value = 'Profile picture updated.'
  } catch (error) {
    avatarError.value = apiErrorMessage(error, 'Could not upload the avatar.')
  } finally {
    avatarBusy.value = false
  }
}

async function removeAvatar() {
  avatarBusy.value = true
  avatarError.value = ''
  avatarMessage.value = ''
  try {
    await auth.deleteAvatar()
    avatarMessage.value = 'Profile picture removed.'
  } catch (error) {
    avatarError.value = apiErrorMessage(error, 'Could not remove the avatar.')
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
          <div class="group relative shrink-0">
            <span
              class="flex h-24 w-24 items-center justify-center overflow-hidden rounded-full border-2 border-background bg-primary/10 text-2xl font-bold text-primary shadow-sm ring-1 ring-border"
            >
              <img
                v-if="auth.avatarObjectUrl"
                :src="auth.avatarObjectUrl"
                alt=""
                class="h-full w-full object-cover"
              />
              <template v-else>{{ auth.initials }}</template>
            </span>
            <button
              type="button"
              class="absolute bottom-0 right-0 flex h-9 w-9 items-center justify-center rounded-full border-2 border-card bg-primary text-primary-foreground shadow-md transition-transform hover:scale-105 hover:bg-primary/90 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary disabled:cursor-not-allowed disabled:opacity-60"
              :disabled="avatarBusy || !auth.user"
              :aria-label="auth.user?.has_avatar ? 'Change profile picture' : 'Upload profile picture'"
              :title="auth.user?.has_avatar ? 'Change profile picture' : 'Upload profile picture'"
              @click="openFilePicker"
            >
              <Loader2 v-if="avatarBusy" class="h-4 w-4 animate-spin" aria-hidden="true" />
              <Camera v-else class="h-4 w-4" aria-hidden="true" />
            </button>
          </div>
          <div class="min-w-0 flex-1">
            <h1 translate="no" class="truncate text-2xl font-bold text-foreground md:text-3xl">
              {{ auth.displayName }}
            </h1>
            <p translate="no" v-if="auth.user?.email" class="mt-1 truncate text-sm text-muted-foreground">
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
            <div class="mt-5 border-t border-border pt-4" :aria-busy="avatarBusy">
              <input
                ref="fileInput"
                type="file"
                class="hidden"
                accept="image/png,image/jpeg"
                @change="onAvatarSelected"
              />
              <p class="text-sm font-medium text-foreground">Profile picture</p>
              <p class="mt-1 text-xs text-muted-foreground">
                PNG or JPEG, up to 512 KB. Your initials are shown when no picture is set.
              </p>
              <div class="mt-3 flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  class="inline-flex h-10 items-center gap-2 rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground shadow-sm transition-colors hover:bg-primary/90 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary disabled:cursor-not-allowed disabled:opacity-60"
                  :disabled="avatarBusy || !auth.user"
                  @click="openFilePicker"
                >
                  <Loader2 v-if="avatarBusy" class="h-4 w-4 animate-spin" aria-hidden="true" />
                  <Camera v-else class="h-4 w-4" aria-hidden="true" />
                  {{
                    avatarBusy
                      ? 'Updating picture…'
                      : auth.user?.has_avatar
                        ? 'Change profile picture'
                        : 'Upload profile picture'
                  }}
                </button>
                <button
                  v-if="auth.user?.has_avatar"
                  type="button"
                  class="inline-flex h-10 items-center gap-2 rounded-md border border-border px-4 text-sm text-muted-foreground transition-colors hover:border-destructive/40 hover:bg-destructive/10 hover:text-destructive focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-destructive disabled:cursor-not-allowed disabled:opacity-60"
                  :disabled="avatarBusy"
                  @click="removeAvatar"
                >
                  <Trash2 class="h-4 w-4" aria-hidden="true" />
                  Remove picture
                </button>
              </div>
            </div>
            <p v-if="avatarMessage" role="status" class="mt-3 text-sm text-primary">
              {{ avatarMessage }}
            </p>
            <p v-if="avatarError" role="alert" class="mt-3 text-sm text-destructive">
              {{ avatarError }}
            </p>
          </div>
        </div>

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
