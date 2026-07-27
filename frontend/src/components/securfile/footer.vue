<script setup lang="ts">
import { FileLock } from 'lucide-vue-next'
import { RouterLink } from 'vue-router'

const productLinks = [
  { label: 'Home', to: '/' },
  { label: 'Product', to: '/upload' },
  { label: 'Education', to: '/community' },
  { label: 'Development Team', to: '/team' },
]
const supportLinks = ['Help Center', 'Contact Us', 'Privacy Policy', 'Terms of Service']
const socialLinks = ['GitHub', 'X', 'Discord']
</script>

<template>
  <footer class="border-t border-border bg-card/50 py-12">
    <div class="container mx-auto px-4">
      <div class="grid md:grid-cols-4 gap-8">
        <div class="md:col-span-2">
          <RouterLink to="/" class="flex items-center gap-2 mb-4 w-fit">
            <div class="p-2 rounded-lg bg-primary/10">
              <FileLock class="h-5 w-5 text-primary" />
            </div>
            <span class="text-lg font-semibold text-foreground">CryptDrop</span>
          </RouterLink>
          <p class="text-muted-foreground text-sm max-w-md">
            CryptDrop provides enterprise-grade file encryption solutions using cutting-edge encryption technology to ensure your sensitive data is always secure.
          </p>
        </div>

        <div>
          <h4 class="text-foreground font-semibold mb-4">Product</h4>
          <ul class="space-y-2 text-sm">
            <li v-for="link in productLinks" :key="link.label">
              <RouterLink :to="link.to" class="text-muted-foreground hover:text-foreground transition-colors">{{ link.label }}</RouterLink>
            </li>
          </ul>
        </div>

        <div>
          <h4 class="text-foreground font-semibold mb-4">Support</h4>
          <ul class="space-y-2 text-sm">
            <li v-for="link in supportLinks" :key="link">
              <a href="#" class="text-muted-foreground hover:text-foreground transition-colors">{{ link }}</a>
            </li>
          </ul>
        </div>
      </div>

      <div class="border-t border-border mt-12 pt-8 flex flex-col md:flex-row items-center justify-between gap-4">
        <p class="text-muted-foreground text-sm">© 2026 CryptDrop. All rights reserved.</p>
        <div class="flex items-center gap-6 text-sm">
          <a
            v-for="link in socialLinks"
            :key="link"
            href="#"
            class="text-muted-foreground hover:text-foreground transition-colors"
          >
            {{ link }}
          </a>
        </div>
      </div>
    </div>
  </footer>
</template>
