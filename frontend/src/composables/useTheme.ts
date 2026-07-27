import { onMounted, ref, watch } from 'vue'

export function useTheme() {
  const theme = ref<'light' | 'dark'>('light')

  const applyTheme = (nextTheme: 'light' | 'dark') => {
    document.documentElement.classList.toggle('dark', nextTheme === 'dark')
  }

  const toggleTheme = () => {
    theme.value = theme.value === 'light' ? 'dark' : 'light'
  }

  onMounted(() => {
    const savedTheme = localStorage.getItem('theme')
    if (savedTheme === 'light' || savedTheme === 'dark') {
      theme.value = savedTheme
    } else if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
      theme.value = 'dark'
    }
  })

  watch(
    theme,
    (nextTheme) => {
      applyTheme(nextTheme)
      localStorage.setItem('theme', nextTheme)
    },
    { immediate: true },
  )

  return { theme, toggleTheme }
}
