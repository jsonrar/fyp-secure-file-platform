<script setup lang="ts">
import { ArrowRight, Sparkles } from 'lucide-vue-next'
import { RouterLink } from 'vue-router'

const highlights = [
  { value: 'AES & RSA', label: 'Encryption' },
  { value: '100%', label: 'Local Encryption' },
  { value: 'Easy Use', label: 'Architecture' },
  { value: '100GB', label: 'File Size' },
]
</script>

<template>
  <section class="py-20 md:py-32">
    <div class="container mx-auto px-4 text-center">
      <div class="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary/10 border border-primary/20 mb-6">
        <Sparkles class="h-4 w-4 text-primary" />
        <span class="text-sm text-primary font-medium">Encrypted File Sharing Platform</span>
      </div>

      <h1 class="text-4xl md:text-6xl lg:text-7xl font-bold text-foreground mb-6 text-balance max-w-4xl mx-auto leading-tight">
        Securely Encrypt and Share Your Sensitive Files
      </h1>

      <p class="text-lg md:text-xl text-muted-foreground max-w-2xl mx-auto mb-10 text-pretty">
        Protect your files with powerful encryption technology. Generate unique keys, share securely, and manage your encrypted files with ease.
      </p>

      <div class="flex flex-col sm:flex-row items-center justify-center gap-4">
        <RouterLink to="/upload" class="h-11 px-8 inline-flex items-center gap-2 rounded-md bg-primary text-primary-foreground hover:bg-primary/90 transition-colors">
          Encrypt Your Files
          <ArrowRight class="h-4 w-4" />
        </RouterLink>
        <RouterLink to="/community" class="h-11 px-8 inline-flex items-center rounded-md border border-border text-foreground hover:bg-secondary transition-colors">
          Learn More
        </RouterLink>
      </div>

      <div class="mt-16 grid grid-cols-2 md:grid-cols-4 gap-8 max-w-3xl mx-auto">
        <div v-for="item in highlights" :key="item.value" class="text-center">
          <div class="text-3xl font-bold text-primary">{{ item.value }}</div>
          <div class="text-sm text-muted-foreground mt-1">{{ item.label }}</div>
        </div>
      </div>
    </div>
  </section>
</template>
