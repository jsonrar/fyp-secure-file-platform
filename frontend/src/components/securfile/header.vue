<script setup lang="ts">
import { Menu, Moon, FileLock, Sun, X } from 'lucide-vue-next'
import { computed } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth_store'

defineProps<{
  isScrolled: boolean
  isMobileMenuOpen: boolean
  theme: 'light' | 'dark'
}>()

const emit = defineEmits<{
  (e: 'toggle-mobile-menu'): void
  (e: 'close-mobile-menu'): void
  (e: 'toggle-theme'): void
}>()

const route = useRoute()
const auth = useAuthStore()

const navLinks = [
  { to: '/upload', label: 'Product', match: ['/upload', '/files', '/audit-logs'] },
  { to: '/community', label: 'Education', match: ['/community'] },
  { to: '/team', label: 'Development Team', match: ['/team'] },
]

const isActive = (match: string[]) => match.some((path) => route.path.startsWith(path))

const homeActive = computed(() => route.path === '/')
</script>

<template>
  <header :class="`border-b border-border bg-card/50 backdrop-blur-sm sticky z-50 transition-all duration-500 ${isScrolled ? 'top-4 mx-4 rounded-2xl shadow-lg' : 'top-0'}`">
    <div class="container mx-auto px-4 py-4">
      <div class="flex items-center justify-between">
        <RouterLink to="/" class="flex items-center gap-2">
          <div class="p-2 rounded-lg bg-primary/10">
            <FileLock class="h-6 w-6 text-primary" />
          </div>
          <span class="text-xl font-semibold text-foreground">CryptDrop</span>
        </RouterLink>

        <nav class="hidden md:flex items-center gap-8">
          <RouterLink
            v-for="link in navLinks"
            :key="link.to"
            :to="link.to"
            class="transition-colors"
            :class="isActive(link.match) ? 'text-foreground font-medium' : 'text-muted-foreground hover:text-foreground'"
          >
            {{ link.label }}
          </RouterLink>
        </nav>

        <div class="hidden md:flex items-center gap-3">
          <button class="h-9 px-3 rounded-md text-muted-foreground hover:bg-secondary transition-colors inline-flex items-center gap-2" @click="emit('toggle-theme')">
            <Sun v-if="theme === 'light'" class="h-4 w-4" />
            <Moon v-else class="h-4 w-4" />
            <span>{{ theme === 'light' ? 'Light' : 'Dark' }}</span>
          </button>
          <RouterLink
            v-if="!auth.isAuthed"
            to="/login"
            class="h-9 px-4 rounded-md text-muted-foreground hover:bg-secondary transition-colors inline-flex items-center"
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
          <RouterLink
            v-else
            to="/upload"
            class="h-9 px-4 rounded-md bg-primary text-primary-foreground hover:bg-primary/90 transition-colors inline-flex items-center"
          >
            Dashboard
          </RouterLink>
        </div>

        <button class="md:hidden h-9 w-9 inline-flex items-center justify-center rounded-md hover:bg-secondary transition-colors" @click="emit('toggle-mobile-menu')">
          <X v-if="isMobileMenuOpen" class="h-5 w-5" />
          <Menu v-else class="h-5 w-5" />
        </button>
      </div>

      <nav v-if="isMobileMenuOpen" class="md:hidden mt-4 pb-4 flex flex-col gap-4">
        <RouterLink
          to="/"
          class="transition-colors py-2"
          :class="homeActive ? 'text-foreground font-medium' : 'text-muted-foreground hover:text-foreground'"
          @click="emit('close-mobile-menu')"
        >
          Home
        </RouterLink>
        <RouterLink
          v-for="link in navLinks"
          :key="`mobile-${link.to}`"
          :to="link.to"
          class="transition-colors py-2"
          :class="isActive(link.match) ? 'text-foreground font-medium' : 'text-muted-foreground hover:text-foreground'"
          @click="emit('close-mobile-menu')"
        >
          {{ link.label }}
        </RouterLink>
        <div class="flex flex-col gap-2 pt-4 border-t border-border">
          <button class="h-9 px-4 rounded-md text-left text-muted-foreground hover:bg-secondary transition-colors inline-flex items-center gap-2" @click="emit('toggle-theme')">
            <Sun v-if="theme === 'light'" class="h-4 w-4" />
            <Moon v-else class="h-4 w-4" />
            <span>{{ theme === 'light' ? 'Light' : 'Dark' }}</span>
          </button>
          <RouterLink
            v-if="!auth.isAuthed"
            to="/login"
            class="h-9 px-4 rounded-md text-left text-muted-foreground hover:bg-secondary transition-colors"
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
        </div>
      </nav>
    </div>
  </header>
</template>
