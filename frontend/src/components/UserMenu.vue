<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { LogOut, Monitor, Moon, Settings, Sun, UserRound } from 'lucide-vue-next'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth_store'
import type { ThemePreference } from '@/composables/useTheme'

const props = defineProps<{
  themePreference: ThemePreference
}>()

const emit = defineEmits<{
  (e: 'set-theme-preference', preference: ThemePreference): void
}>()

const router = useRouter()
const auth = useAuthStore()

const isOpen = ref(false)
const root = ref<HTMLElement | null>(null)

/**
 * The panel hangs below the avatar with a gap between them. Closing the instant the pointer
 * leaves the button would make the menu unreachable, so a leave is a scheduled close that
 * entering either element cancels.
 */
let closeTimer = 0

const themeOptions: { value: ThemePreference; label: string; icon: typeof Sun }[] = [
  { value: 'system', label: 'System', icon: Monitor },
  { value: 'light', label: 'Light', icon: Sun },
  { value: 'dark', label: 'Dark', icon: Moon },
]

const currentTheme = computed(
  () => themeOptions.find((option) => option.value === props.themePreference) ?? themeOptions[0],
)

function cancelClose() {
  window.clearTimeout(closeTimer)
  closeTimer = 0
}

function open() {
  cancelClose()
  isOpen.value = true
}

function scheduleClose() {
  cancelClose()
  closeTimer = window.setTimeout(() => {
    isOpen.value = false
  }, 180)
}

function close() {
  cancelClose()
  isOpen.value = false
}

function goToProfile() {
  close()
  router.push('/profile')
}

function goToSettings() {
  close()
  router.push('/settings')
}

function selectTheme(preference: ThemePreference) {
  emit('set-theme-preference', preference)
}

function handleLogout() {
  close()
  auth.logout()
  router.push('/login')
}

function onDocumentPointerDown(event: PointerEvent) {
  const target = event.target as Node | null
  if (target && root.value?.contains(target)) return
  close()
}

function onKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape') close()
}

onMounted(() => {
  document.addEventListener('pointerdown', onDocumentPointerDown)
  document.addEventListener('keydown', onKeydown)
  // Only mounted while signed in, so this is the natural place to learn who that is.
  void auth.loadUser()
})

onBeforeUnmount(() => {
  document.removeEventListener('pointerdown', onDocumentPointerDown)
  document.removeEventListener('keydown', onKeydown)
  cancelClose()
})
</script>

<template>
  <div
    ref="root"
    class="relative shrink-0"
    @mouseenter="open"
    @mouseleave="scheduleClose"
  >
    <button
      type="button"
      class="flex h-9 w-9 items-center justify-center rounded-full border border-border bg-primary/10 text-sm font-semibold text-primary transition-colors hover:border-primary/60 hover:bg-primary/20 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
      :aria-expanded="isOpen"
      aria-haspopup="menu"
      :aria-label="`Account menu for ${auth.displayName}`"
      @click="goToProfile"
      @focus="open"
    >
      {{ auth.initials }}
    </button>

    <div
      v-if="isOpen"
      role="menu"
      class="absolute right-0 top-full z-[60] mt-2 w-60 overflow-hidden rounded-xl border border-border bg-card shadow-lg"
    >
      <button
        type="button"
        role="menuitem"
        class="flex w-full items-center gap-3 border-b border-border px-4 py-3 text-left transition-colors hover:bg-secondary"
        @click="goToProfile"
      >
        <span
          class="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-primary/10 text-sm font-semibold text-primary"
        >
          {{ auth.initials }}
        </span>
        <span class="min-w-0">
          <span class="block truncate text-sm font-medium text-foreground">{{ auth.displayName }}</span>
          <span v-if="auth.user?.email" class="block truncate text-xs text-muted-foreground">
            {{ auth.user.email }}
          </span>
        </span>
      </button>

      <div class="py-1">
        <button
          type="button"
          role="menuitem"
          class="flex w-full items-center gap-2.5 px-4 py-2 text-left text-sm text-foreground transition-colors hover:bg-secondary"
          @click="goToProfile"
        >
          <UserRound class="h-4 w-4 shrink-0 text-muted-foreground" />
          Profile
        </button>
      </div>

      <div class="border-t border-border px-4 py-2">
        <p class="mb-1.5 text-[0.7rem] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
          Theme · {{ currentTheme.label }}
        </p>
        <div class="grid grid-cols-3 gap-1">
          <button
            v-for="option in themeOptions"
            :key="option.value"
            type="button"
            role="menuitemradio"
            :aria-checked="themePreference === option.value"
            class="flex flex-col items-center gap-1 rounded-md border px-1 py-2 text-[0.7rem] transition-colors"
            :class="
              themePreference === option.value
                ? 'border-primary bg-primary/10 text-foreground'
                : 'border-transparent text-muted-foreground hover:bg-secondary hover:text-foreground'
            "
            @click="selectTheme(option.value)"
          >
            <component :is="option.icon" class="h-4 w-4" />
            {{ option.label }}
          </button>
        </div>
      </div>

      <div class="border-t border-border py-1">
        <button
          type="button"
          role="menuitem"
          class="flex w-full items-center gap-2.5 px-4 py-2 text-left text-sm text-foreground transition-colors hover:bg-secondary"
          @click="goToSettings"
        >
          <Settings class="h-4 w-4 shrink-0 text-muted-foreground" />
          Settings
        </button>
        <button
          type="button"
          role="menuitem"
          class="flex w-full items-center gap-2.5 px-4 py-2 text-left text-sm text-destructive transition-colors hover:bg-destructive/10"
          @click="handleLogout"
        >
          <LogOut class="h-4 w-4 shrink-0" />
          Log out
        </button>
      </div>
    </div>
  </div>
</template>
