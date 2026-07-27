<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { RouterView } from 'vue-router'
import AppHeader from '@/components/securfile/header.vue'
import AppFooter from '@/components/securfile/footer.vue'
import { useTheme } from '@/composables/useTheme'

const isScrolled = ref(false)
const isMobileMenuOpen = ref(false)
const { theme, toggleTheme } = useTheme()

const onScroll = () => {
  isScrolled.value = window.scrollY > 20
}

onMounted(() => {
  window.addEventListener('scroll', onScroll)
  onScroll()
})

onBeforeUnmount(() => {
  window.removeEventListener('scroll', onScroll)
})
</script>

<template>
  <main class="min-h-screen bg-background">
    <AppHeader
      :is-scrolled="isScrolled"
      :is-mobile-menu-open="isMobileMenuOpen"
      :theme="theme"
      @toggle-mobile-menu="isMobileMenuOpen = !isMobileMenuOpen"
      @close-mobile-menu="isMobileMenuOpen = false"
      @toggle-theme="toggleTheme"
    />
    <RouterView />
    <AppFooter />
  </main>
</template>
