<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { ChevronDown, Menu, Monitor, Moon, Settings, Sun, UserRound, X } from 'lucide-vue-next'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import SecureViewMark from '@/components/brand/SecureViewMark.vue'
import UserMenu from '@/components/UserMenu.vue'
import { useAuthStore } from '@/stores/auth_store'
import type { ThemePreference } from '@/composables/useTheme'

const props = defineProps<{
  isScrolled: boolean
  isMobileMenuOpen: boolean
  themePreference: ThemePreference
}>()

const emit = defineEmits<{
  (e: 'toggle-mobile-menu'): void
  (e: 'close-mobile-menu'): void
  (e: 'set-theme-preference', preference: ThemePreference): void
}>()

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

// Signed out, "Product" is the marketing entry into the encryption page. Signed in, the
// three authenticated pages get their own links: /files and /audit-logs existed but were
// reachable only by typing the URL, so managing or sharing an already-uploaded file had
// no entry point at all.
const guestLinks = [
  { to: '/upload', label: 'Product', match: ['/upload', '/files', '/audit-logs'] },
  { to: '/education', label: 'Education', match: ['/education'] },
  { to: '/team', label: 'Development Team', match: ['/team'] },
]

const authedLinks = [
  { to: '/upload', label: 'Upload', match: ['/upload'] },
  { to: '/files', label: 'My Files', match: ['/files'] },
  { to: '/audit-logs', label: 'Access Records', match: ['/audit-logs'] },
  { to: '/education', label: 'Education', match: ['/education'] },
  { to: '/team', label: 'Development Team', match: ['/team'] },
]

const navLinks = computed(() => (auth.isAuthed ? authedLinks : guestLinks))

const isActive = (match: string[]) => match.some((path) => route.path.startsWith(path))

const homeActive = computed(() => route.path === '/')

/** Header chrome text: black in Light, white in Dark — not the muted theme token. */
const headerText = 'text-black dark:text-white'
const headerNavLink = (active: boolean) =>
  active ? `${headerText} font-medium` : `${headerText} opacity-70 hover:opacity-100`

/**
 * Fixed trigger width sized for the longest label ("System") so switching Light/Dark/System
 * never changes the control's box and cannot shove neighbouring header actions sideways.
 */
const themeTriggerClass =
  `h-9 w-[7.25rem] shrink-0 rounded-md ${headerText} hover:bg-secondary transition-colors ` +
  'inline-flex items-center justify-between gap-1 px-3'

const themeOptions: {
  value: ThemePreference
  label: string
  icon: typeof Sun
}[] = [
  { value: 'system', label: 'System', icon: Monitor },
  { value: 'light', label: 'Light', icon: Sun },
  { value: 'dark', label: 'Dark', icon: Moon },
]

const currentThemeOption = computed(
  () => themeOptions.find((option) => option.value === props.themePreference) ?? themeOptions[0],
)

const desktopThemeOpen = ref(false)
const mobileThemeOpen = ref(false)
const desktopThemeRoot = ref<HTMLElement | null>(null)
const mobileThemeRoot = ref<HTMLElement | null>(null)

function closeThemeMenus() {
  desktopThemeOpen.value = false
  mobileThemeOpen.value = false
}

function toggleDesktopTheme() {
  desktopThemeOpen.value = !desktopThemeOpen.value
  mobileThemeOpen.value = false
}

function toggleMobileTheme() {
  mobileThemeOpen.value = !mobileThemeOpen.value
  desktopThemeOpen.value = false
}

function selectTheme(preference: ThemePreference) {
  emit('set-theme-preference', preference)
  closeThemeMenus()
}

function onDocumentPointerDown(event: PointerEvent) {
  const target = event.target as Node | null
  if (!target) return
  if (desktopThemeRoot.value?.contains(target)) return
  if (mobileThemeRoot.value?.contains(target)) return
  closeThemeMenus()
}

onMounted(() => {
  document.addEventListener('pointerdown', onDocumentPointerDown)
})

onBeforeUnmount(() => {
  document.removeEventListener('pointerdown', onDocumentPointerDown)
})

watch(
  () => props.isMobileMenuOpen,
  (open) => {
    if (!open) closeThemeMenus()
  },
)

function handleLogout() {
  auth.logout()
  emit('close-mobile-menu')
  router.push('/login')
}
</script>

<template>
  <header :class="`border-b border-border bg-card/50 backdrop-blur-sm sticky z-50 transition-all duration-500 ${isScrolled ? 'top-4 mx-4 rounded-2xl shadow-lg' : 'top-0'}`">
    <div class="container mx-auto px-4 py-4">
      <div class="flex items-center justify-between">
        <RouterLink
          to="/"
          :class="`inline-flex items-center ${headerText}`"
          aria-label="SecureView home"
        >
          <SecureViewMark variant="logo" class="h-9" />
        </RouterLink>

        <nav class="hidden md:flex items-center gap-6">
          <RouterLink
            v-for="link in navLinks"
            :key="link.to"
            :to="link.to"
            class="transition-opacity"
            :class="headerNavLink(isActive(link.match))"
          >
            {{ link.label }}
          </RouterLink>
        </nav>

        <div class="hidden md:flex items-center gap-3">
          <!-- Signed in, the theme control lives in the avatar menu instead: one account
               dropdown rather than two adjacent dropdowns in the same corner. -->
          <div v-if="!auth.isAuthed" ref="desktopThemeRoot" class="relative shrink-0">
            <button
              type="button"
              :class="themeTriggerClass"
              :aria-expanded="desktopThemeOpen"
              aria-haspopup="listbox"
              aria-label="Theme"
              @click="toggleDesktopTheme"
            >
              <span class="inline-flex min-w-0 items-center gap-1.5">
                <component :is="currentThemeOption.icon" class="h-4 w-4 shrink-0" />
                <span class="truncate text-sm">{{ currentThemeOption.label }}</span>
              </span>
              <ChevronDown
                class="h-3.5 w-3.5 shrink-0 opacity-70 transition-transform"
                :class="desktopThemeOpen ? 'rotate-180' : ''"
              />
            </button>
            <ul
              v-if="desktopThemeOpen"
              role="listbox"
              class="absolute right-0 top-full z-[60] mt-1 w-[7.25rem] overflow-hidden rounded-md border border-border bg-card py-1 shadow-lg"
            >
              <li v-for="option in themeOptions" :key="option.value">
                <button
                  type="button"
                  role="option"
                  :aria-selected="themePreference === option.value"
                  class="flex w-full items-center gap-1.5 px-3 py-2 text-left text-sm transition-colors hover:bg-secondary"
                  :class="themePreference === option.value ? `${headerText} font-medium` : `${headerText} opacity-70`"
                  @click="selectTheme(option.value)"
                >
                  <component :is="option.icon" class="h-4 w-4 shrink-0" />
                  <span>{{ option.label }}</span>
                </button>
              </li>
            </ul>
          </div>
          <RouterLink
            v-if="!auth.isAuthed"
            to="/login"
            :class="`h-9 px-4 rounded-md ${headerText} hover:bg-secondary transition-colors inline-flex items-center`"
          >
            Sign In
          </RouterLink>
          <RouterLink
            v-if="!auth.isAuthed"
            to="/register"
            class="h-9 px-4 rounded-md bg-primary text-primary-foreground hover:bg-primary/90 transition-colors inline-flex items-center"
          >
            Get Started
          </RouterLink>
          <template v-else>
            <RouterLink
              to="/dashboard"
              class="h-9 px-4 rounded-md bg-primary text-primary-foreground hover:bg-primary/90 transition-colors inline-flex items-center"
            >
              Dashboard
            </RouterLink>
            <UserMenu
              :theme-preference="themePreference"
              @set-theme-preference="emit('set-theme-preference', $event)"
            />
          </template>
        </div>

        <button
          :class="`md:hidden h-9 w-9 inline-flex items-center justify-center rounded-md ${headerText} hover:bg-secondary transition-colors`"
          @click="emit('toggle-mobile-menu')"
        >
          <X v-if="isMobileMenuOpen" class="h-5 w-5" />
          <Menu v-else class="h-5 w-5" />
        </button>
      </div>

      <nav v-if="isMobileMenuOpen" class="md:hidden mt-4 pb-4 flex flex-col gap-4">
        <RouterLink
          to="/"
          class="transition-opacity py-2"
          :class="headerNavLink(homeActive)"
          @click="emit('close-mobile-menu')"
        >
          Home
        </RouterLink>
        <RouterLink
          v-for="link in navLinks"
          :key="`mobile-${link.to}`"
          :to="link.to"
          class="transition-opacity py-2"
          :class="headerNavLink(isActive(link.match))"
          @click="emit('close-mobile-menu')"
        >
          {{ link.label }}
        </RouterLink>
        <div class="flex flex-col gap-2 pt-4 border-t border-border">
          <div ref="mobileThemeRoot" class="relative w-[7.25rem] shrink-0">
            <button
              type="button"
              :class="themeTriggerClass"
              :aria-expanded="mobileThemeOpen"
              aria-haspopup="listbox"
              aria-label="Theme"
              @click="toggleMobileTheme"
            >
              <span class="inline-flex min-w-0 items-center gap-1.5">
                <component :is="currentThemeOption.icon" class="h-4 w-4 shrink-0" />
                <span class="truncate text-sm">{{ currentThemeOption.label }}</span>
              </span>
              <ChevronDown
                class="h-3.5 w-3.5 shrink-0 opacity-70 transition-transform"
                :class="mobileThemeOpen ? 'rotate-180' : ''"
              />
            </button>
            <ul
              v-if="mobileThemeOpen"
              role="listbox"
              class="absolute left-0 top-full z-[60] mt-1 w-[7.25rem] overflow-hidden rounded-md border border-border bg-card py-1 shadow-lg"
            >
              <li v-for="option in themeOptions" :key="`mobile-${option.value}`">
                <button
                  type="button"
                  role="option"
                  :aria-selected="themePreference === option.value"
                  class="flex w-full items-center gap-1.5 px-3 py-2 text-left text-sm transition-colors hover:bg-secondary"
                  :class="themePreference === option.value ? `${headerText} font-medium` : `${headerText} opacity-70`"
                  @click="selectTheme(option.value)"
                >
                  <component :is="option.icon" class="h-4 w-4 shrink-0" />
                  <span>{{ option.label }}</span>
                </button>
              </li>
            </ul>
          </div>
          <RouterLink
            v-if="!auth.isAuthed"
            to="/login"
            :class="`h-9 px-4 rounded-md text-left ${headerText} hover:bg-secondary transition-colors`"
            @click="emit('close-mobile-menu')"
          >
            Sign In
          </RouterLink>
          <RouterLink
            v-if="!auth.isAuthed"
            to="/register"
            class="h-9 px-4 rounded-md bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
            @click="emit('close-mobile-menu')"
          >
            Get Started
          </RouterLink>
          <template v-else>
            <RouterLink
              to="/dashboard"
              class="h-9 px-4 rounded-md bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
              @click="emit('close-mobile-menu')"
            >
              Dashboard
            </RouterLink>
            <!-- Touch has no hover, so the avatar dropdown's destinations are listed here. -->
            <RouterLink
              to="/profile"
              :class="`h-9 px-4 rounded-md inline-flex items-center gap-2 ${headerText} hover:bg-secondary transition-colors`"
              @click="emit('close-mobile-menu')"
            >
              <UserRound class="h-4 w-4 shrink-0" />
              Profile
            </RouterLink>
            <RouterLink
              to="/settings"
              :class="`h-9 px-4 rounded-md inline-flex items-center gap-2 ${headerText} hover:bg-secondary transition-colors`"
              @click="emit('close-mobile-menu')"
            >
              <Settings class="h-4 w-4 shrink-0" />
              Settings
            </RouterLink>
            <button
              :class="`h-9 px-4 rounded-md text-left ${headerText} hover:bg-secondary transition-colors`"
              @click="handleLogout"
            >
              Log Out
            </button>
          </template>
        </div>
      </nav>
    </div>
  </header>
</template>
