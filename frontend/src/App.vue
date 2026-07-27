<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { RouterView, useRoute } from 'vue-router'
import AppHeader from '@/components/securfile/header.vue'
import AppFooter from '@/components/securfile/footer.vue'
import { useTheme } from '@/composables/useTheme'

const route = useRoute()
const isScrolled = ref(false)
const isMobileMenuOpen = ref(false)
const { theme, toggleTheme } = useTheme()

const hideChrome = computed(() => ['/login', '/register'].includes(route.path))

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
      v-if="!hideChrome"
      :is-scrolled="isScrolled"
      :is-mobile-menu-open="isMobileMenuOpen"
      :theme="theme"
      @toggle-mobile-menu="isMobileMenuOpen = !isMobileMenuOpen"
      @close-mobile-menu="isMobileMenuOpen = false"
      @toggle-theme="toggleTheme"
    />
    <RouterView />
    <AppFooter v-if="!hideChrome" />
  </main>
</template>
