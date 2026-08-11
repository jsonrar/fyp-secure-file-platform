<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { RouterView, useRoute } from 'vue-router'
import AppHeader from '@/components/securfile/header.vue'
import AppFooter from '@/components/securfile/footer.vue'
import { useTheme } from '@/composables/useTheme'

const route = useRoute()
const isScrolled = ref(false)
const isMobileMenuOpen = ref(false)
const { theme, toggleTheme } = useTheme()

watch(
  () => route.fullPath,
  () => {
    isMobileMenuOpen.value = false
    window.scrollTo({ top: 0, left: 0, behavior: 'auto' })
  },
)

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
