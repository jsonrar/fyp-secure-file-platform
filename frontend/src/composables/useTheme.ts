import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

export type ThemePreference = 'system' | 'light' | 'dark'
export type ResolvedTheme = 'light' | 'dark'

const STORAGE_KEY = 'theme'

function systemPrefersDark(): boolean {
  return window.matchMedia('(prefers-color-scheme: dark)').matches
}

function resolveTheme(preference: ThemePreference): ResolvedTheme {
  if (preference === 'light' || preference === 'dark') return preference
  return systemPrefersDark() ? 'dark' : 'light'
}

function isThemePreference(value: string | null): value is ThemePreference {
  return value === 'system' || value === 'light' || value === 'dark'
}

function readStoredPreference(): ThemePreference {
  if (typeof window === 'undefined') return 'system'
  const saved = localStorage.getItem(STORAGE_KEY)
  return isThemePreference(saved) ? saved : 'system'
}

export function useTheme() {
  const preference = ref<ThemePreference>(readStoredPreference())
  const resolvedTheme = computed(() => resolveTheme(preference.value))

  const applyTheme = (nextTheme: ResolvedTheme) => {
    document.documentElement.classList.toggle('dark', nextTheme === 'dark')
  }

  const setPreference = (next: ThemePreference) => {
    preference.value = next
  }

  let mediaQuery: MediaQueryList | null = null

  const onSystemChange = () => {
    if (preference.value === 'system') {
      applyTheme(resolveTheme('system'))
    }
  }

  onMounted(() => {
    mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
    mediaQuery.addEventListener('change', onSystemChange)
  })

  onBeforeUnmount(() => {
    mediaQuery?.removeEventListener('change', onSystemChange)
  })

  watch(
    preference,
    (next) => {
      applyTheme(resolveTheme(next))
      localStorage.setItem(STORAGE_KEY, next)
    },
    { immediate: true },
  )

  return { preference, resolvedTheme, setPreference }
}
