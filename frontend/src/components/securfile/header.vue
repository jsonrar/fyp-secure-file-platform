<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { ChevronDown, Menu, Monitor, Moon, Settings, Sun, UserRound, X } from 'lucide-vue-next'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import SecureViewMark from '@/components/brand/SecureViewMark.vue'
import UserMenu from '@/components/UserMenu.vue'
import LanguageSwitcher from '@/components/LanguageSwitcher.vue'
import { useI18n } from 'vue-i18n'
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
const { t } = useI18n()

// Signed out: what it is (Product, the feature overview on the home page), how it works, how to
// use it (Help), the background (Education), then Contact us. "Product" used to point at /upload,
// which only redirects a visitor to sign in. Signed in, the three authenticated pages get their own
// links: /files and /audit-logs existed but were reachable only by typing the URL, so managing or
// sharing an already-uploaded file had no entry point at all.
const guestLinks = [
  { to: '/#features', label: 'nav.product', match: [] as string[] },
  { to: '/how-it-works', label: 'nav.howItWorks', match: ['/how-it-works'] },
  { to: '/help', label: 'nav.help', match: ['/help'] },
  { to: '/education', label: 'nav.education', match: ['/education'] },
  { to: '/team', label: 'nav.contact', match: ['/team'] },
]

const authedLinks = [
  { to: '/upload', label: 'nav.upload', match: ['/upload'] },
  { to: '/files', label: 'nav.myFiles', match: ['/files'] },
  { to: '/audit-logs', label: 'nav.accessRecords', match: ['/audit-logs'] },
  { to: '/help', label: 'nav.help', match: ['/help'] },
  { to: '/education', label: 'nav.education', match: ['/education'] },
  { to: '/team', label: 'nav.contact', match: ['/team'] },
]

// Administrators and recovery officers get their console in the header. It used to be reachable
// only through the avatar menu's "Operations" item, which every user sees, so an administrator
// could sign in and find nothing that looked different.
const navLinks = computed(() => {
  if (!auth.isAuthed) return guestLinks
  if (!auth.isRecoveryReviewer) return authedLinks
  const label = auth.isAdmin ? 'nav.admin' : 'nav.recovery'
  return [...authedLinks, { to: '/admin', label, match: ['/admin'] }]
})

// The full header does not fit below 1024px: signed in, the last links slid under the Dashboard
// button; signed out, "Contact us" ran into the theme menu at 768px. Below lg both use the menu
// button. Full class names, so Tailwind sees them.
const responsive = computed(() => ({ desktop: 'hidden lg:flex', mobile: 'lg:hidden' }))

const isActive = (match: string[]) => match.some((path) => route.path.startsWith(path))

const homeActive = computed(() => route.path === '/')

/** Header chrome text: black in Light, white in Dark — not the muted theme token. */
const headerText = 'text-black dark:text-white'
const headerNavLink = (active: boolean) =>
  active
    ? 'text-primary font-medium'
    : `${headerText} opacity-70 hover:opacity-100 hover:text-primary`

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
  { value: 'system', label: 'theme.system', icon: Monitor },
  { value: 'light', label: 'theme.light', icon: Sun },
  { value: 'dark', label: 'theme.dark', icon: Moon },
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

async function handleLogout() {
  await auth.logout()
  emit('close-mobile-menu')
  router.push('/login')
}
</script>

<template>
  <header :class="`border-b border-border bg-card/50 backdrop-blur-sm sticky z-50 transition-all duration-500 ${isScrolled ? 'top-4 mx-4 rounded-2xl shadow-lg' : 'top-0'}`">
    <div class="w-full py-4 pl-2 pr-4 sm:pl-3 sm:pr-5 lg:pl-4 lg:pr-6">
      <div class="flex items-center justify-between gap-4">
        <div class="flex min-w-0 items-center gap-5 md:gap-8">
          <RouterLink
            to="/"
            :class="`inline-flex shrink-0 items-center ${headerText}`"
            :aria-label="t('nav.homeAria')"
          >
            <SecureViewMark variant="logo" class="h-9" />
          </RouterLink>

          <nav :class="`${responsive.desktop} items-center gap-7 lg:gap-6 xl:gap-9`">
            <RouterLink
              v-for="link in navLinks"
              :key="link.to"
              :to="link.to"
              class="transition-colors whitespace-nowrap"
              :class="headerNavLink(isActive(link.match))"
            >
              {{ t(link.label) }}
            </RouterLink>
          </nav>
        </div>

        <div :class="`${responsive.desktop} items-center gap-3 shrink-0`">
          <LanguageSwitcher />
          <!-- Signed in, the theme control lives in the avatar menu instead: one account
               dropdown rather than two adjacent dropdowns in the same corner. -->
          <div v-if="!auth.isAuthed" ref="desktopThemeRoot" class="relative shrink-0">
            <button
              type="button"
              :class="themeTriggerClass"
              :aria-expanded="desktopThemeOpen"
              aria-haspopup="listbox"
              :aria-label="t('theme.label')"
              @click="toggleDesktopTheme"
            >
              <span class="inline-flex min-w-0 items-center gap-1.5">
                <component :is="currentThemeOption.icon" class="h-4 w-4 shrink-0" />
                <span class="truncate text-sm">{{ t(currentThemeOption.label) }}</span>
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
                  <span>{{ t(option.label) }}</span>
                </button>
              </li>
            </ul>
          </div>
          <RouterLink
            v-if="!auth.isAuthed"
            to="/login"
            :class="`h-9 px-4 rounded-md ${headerText} hover:bg-secondary transition-colors inline-flex items-center`"
          >
            {{ t('nav.signIn') }}
          </RouterLink>
          <RouterLink
            v-if="!auth.isAuthed"
            to="/register"
            class="h-9 px-4 rounded-md bg-primary text-primary-foreground hover:bg-primary/90 transition-colors inline-flex items-center"
          >
            {{ t('nav.getStarted') }}
          </RouterLink>
          <template v-else>
            <RouterLink
              to="/dashboard"
              class="h-9 px-4 rounded-md bg-primary text-primary-foreground hover:bg-primary/90 transition-colors inline-flex items-center"
            >
              {{ t('nav.dashboard') }}
            </RouterLink>
            <UserMenu
              :theme-preference="themePreference"
              @set-theme-preference="emit('set-theme-preference', $event)"
            />
          </template>
        </div>

        <button
          :class="`${responsive.mobile} h-9 w-9 inline-flex items-center justify-center rounded-md ${headerText} hover:bg-secondary transition-colors`"
          :aria-label="t(isMobileMenuOpen ? 'nav.closeMenu' : 'nav.openMenu')"
          :aria-expanded="isMobileMenuOpen"
          @click="emit('toggle-mobile-menu')"
        >
          <X v-if="isMobileMenuOpen" class="h-5 w-5" />
          <Menu v-else class="h-5 w-5" />
        </button>
      </div>

      <nav v-if="isMobileMenuOpen" :class="`${responsive.mobile} mt-4 pb-4 flex flex-col gap-4`">
        <RouterLink
          to="/"
          class="transition-colors py-2"
          :class="headerNavLink(homeActive)"
          @click="emit('close-mobile-menu')"
        >
          {{ t('nav.home') }}
        </RouterLink>
        <RouterLink
          v-for="link in navLinks"
          :key="`mobile-${link.to}`"
          :to="link.to"
          class="transition-colors py-2"
          :class="headerNavLink(isActive(link.match))"
          @click="emit('close-mobile-menu')"
        >
          {{ t(link.label) }}
        </RouterLink>
        <div class="flex flex-col gap-2 pt-4 border-t border-border">
          <LanguageSwitcher class="w-fit" />
          <div ref="mobileThemeRoot" class="relative w-[7.25rem] shrink-0">
            <button
              type="button"
              :class="themeTriggerClass"
              :aria-expanded="mobileThemeOpen"
              aria-haspopup="listbox"
              :aria-label="t('theme.label')"
              @click="toggleMobileTheme"
            >
              <span class="inline-flex min-w-0 items-center gap-1.5">
                <component :is="currentThemeOption.icon" class="h-4 w-4 shrink-0" />
                <span class="truncate text-sm">{{ t(currentThemeOption.label) }}</span>
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
                  <span>{{ t(option.label) }}</span>
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
            {{ t('nav.signIn') }}
          </RouterLink>
          <RouterLink
            v-if="!auth.isAuthed"
            to="/register"
            class="h-9 px-4 rounded-md bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
            @click="emit('close-mobile-menu')"
          >
            {{ t('nav.getStarted') }}
          </RouterLink>
          <template v-else>
            <RouterLink
              to="/dashboard"
              class="h-9 px-4 rounded-md bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
              @click="emit('close-mobile-menu')"
            >
              {{ t('nav.dashboard') }}
            </RouterLink>
            <!-- Touch has no hover, so the avatar dropdown's destinations are listed here. -->
            <RouterLink
              to="/profile"
              :class="`h-9 px-4 rounded-md inline-flex items-center gap-2 ${headerText} hover:bg-secondary transition-colors`"
              @click="emit('close-mobile-menu')"
            >
              <UserRound class="h-4 w-4 shrink-0" />
              {{ t('nav.profile') }}
            </RouterLink>
            <RouterLink
              to="/settings"
              :class="`h-9 px-4 rounded-md inline-flex items-center gap-2 ${headerText} hover:bg-secondary transition-colors`"
              @click="emit('close-mobile-menu')"
            >
              <Settings class="h-4 w-4 shrink-0" />
              {{ t('nav.settings') }}
            </RouterLink>
            <button
              :class="`h-9 px-4 rounded-md text-left ${headerText} hover:bg-secondary transition-colors`"
              @click="handleLogout"
            >
              {{ t('nav.logOut') }}
            </button>
          </template>
        </div>
      </nav>
    </div>
  </header>
</template>
