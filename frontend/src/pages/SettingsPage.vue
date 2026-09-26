<script setup lang="ts">
import { ref } from 'vue'
import { LogOut, Monitor, Moon, Sun, UserRound } from 'lucide-vue-next'
import { RouterLink, useRouter } from 'vue-router'
import DeleteAccountDialog from '@/components/DeleteAccountDialog.vue'
import ResetPassphraseCard from '@/components/ResetPassphraseCard.vue'
import { useTheme, type ThemePreference } from '@/composables/useTheme'
import { useAuthStore } from '@/stores/auth_store'

const router = useRouter()
const auth = useAuthStore()
const { preference, setPreference } = useTheme()
const showDelete = ref(false)

const themeOptions: { value: ThemePreference; label: string; hint: string; icon: typeof Sun }[] = [
  { value: 'system', label: 'System', hint: 'Follow the operating system', icon: Monitor },
  { value: 'light', label: 'Light', hint: 'Always light', icon: Sun },
  { value: 'dark', label: 'Dark', hint: 'Always dark', icon: Moon },
]

async function handleLogout() {
  await auth.logout()
  router.push('/login')
}

/**
 * The account is gone server-side; clear the local session so the app does not keep
 * rendering a signed-in shell against a user that no longer exists. Sessions were already
 * revoked with the account — do not call `POST /auth/logout` against a deleted user.
 */
function onDeleted() {
  showDelete.value = false
  auth.clearLocalSession()
  router.push({ path: '/register', query: { deleted: '1' } })
}
</script>

<template>
  <section class="py-16 md:py-24">
    <div class="container mx-auto max-w-3xl px-4">
      <h1 class="text-2xl font-bold text-foreground md:text-3xl">Settings</h1>
      <p class="mt-2 text-sm text-muted-foreground">
        Appearance and account controls for {{ auth.displayName }}.
      </p>

      <div class="mt-8 rounded-xl border border-border bg-card p-6">
        <h2 class="text-lg font-semibold text-foreground">Appearance</h2>
        <p class="mt-1 text-sm text-muted-foreground">
          Applies immediately and is remembered on this device.
        </p>

        <div class="mt-4 grid gap-3 sm:grid-cols-3">
          <button
            v-for="option in themeOptions"
            :key="option.value"
            type="button"
            role="radio"
            :aria-checked="preference === option.value"
            class="rounded-lg border p-4 text-left transition-colors"
            :class="
              preference === option.value
                ? 'border-primary bg-primary/10'
                : 'border-border hover:border-primary/40'
            "
            @click="setPreference(option.value)"
          >
            <component
              :is="option.icon"
              class="mb-2 h-5 w-5"
              :class="preference === option.value ? 'text-primary' : 'text-muted-foreground'"
            />
            <p class="text-sm font-semibold text-foreground">{{ option.label }}</p>
            <p class="mt-1 text-xs text-muted-foreground">{{ option.hint }}</p>
          </button>
        </div>
      </div>

      <div class="mt-6 rounded-xl border border-border bg-card p-6">
        <h2 class="text-lg font-semibold text-foreground">Account</h2>
        <div class="mt-4 flex flex-wrap gap-3">
          <RouterLink
            to="/profile"
            class="inline-flex h-10 items-center gap-2 rounded-md border border-border px-4 text-sm text-foreground transition-colors hover:bg-secondary"
          >
            <UserRound class="h-4 w-4" />
            View profile
          </RouterLink>
          <button
            type="button"
            class="inline-flex h-10 items-center gap-2 rounded-md border border-border px-4 text-sm text-foreground transition-colors hover:bg-secondary"
            @click="handleLogout"
          >
            <LogOut class="h-4 w-4" />
            Log out
          </button>
        </div>
      </div>

      <ResetPassphraseCard />

      <div class="mt-6 rounded-xl border border-destructive/40 bg-card p-6">
        <h2 class="text-lg font-semibold text-foreground">Delete this account</h2>
        <p class="mt-2 max-w-2xl text-sm text-muted-foreground">
          Removes the account and every file uploaded from it. There is no way to reverse this
          and no way to recover the files afterwards. If you are locked out by a forgotten
          passphrase, reset it above with your saved private key file instead.
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
