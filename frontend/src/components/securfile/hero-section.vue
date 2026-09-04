<script setup lang="ts">
import { ArrowRight, Sparkles } from 'lucide-vue-next'
import { RouterLink } from 'vue-router'

const highlights = [
  { value: 'AES & RSA', label: 'Encryption' },
  { value: '100%', label: 'Local Encryption' },
  { value: 'Easy Use', label: 'Architecture' },
  { value: '25GB', label: 'File Size' },
]
</script>

<template>
  <section class="relative overflow-hidden py-20 md:py-28">
    <div class="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_50%_28%,color-mix(in_oklab,var(--primary)_16%,transparent),transparent_58%)]" />

    <div class="container relative mx-auto px-4">
      <div class="mx-auto flex max-w-4xl flex-col items-center text-center">
        <div class="mb-6 inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/10 px-4 py-2">
          <Sparkles class="h-4 w-4 text-primary" />
          <span class="text-sm font-medium text-primary">Encrypted File Sharing Platform</span>
        </div>

        <h1 class="mb-6 max-w-4xl text-4xl font-bold tracking-tight text-foreground sm:text-5xl md:text-6xl">
          Encryption
          <span class="text-primary"> and Sharing</span>
        </h1>

        <p class="mb-10 max-w-2xl text-base text-muted-foreground md:text-xl">
          Protect your files with powerful encryption technology. Generate unique keys, share securely,
          and manage your encrypted files with ease.
        </p>

        <div class="flex flex-col items-center justify-center gap-4 sm:flex-row">
          <RouterLink
            to="/upload"
            class="inline-flex h-11 items-center gap-2 rounded-full bg-primary px-8 text-primary-foreground transition-colors hover:bg-primary/90"
          >
            Encrypt Your Files
            <ArrowRight class="h-4 w-4" />
          </RouterLink>
          <RouterLink
            to="/education"
            class="inline-flex h-11 items-center rounded-full border border-border px-8 text-foreground transition-colors hover:bg-secondary"
          >
            Learn More
          </RouterLink>
        </div>

        <div class="mt-16 grid w-full max-w-3xl grid-cols-2 gap-8 md:grid-cols-4">
          <div v-for="item in highlights" :key="item.value" class="text-center">
            <div class="text-3xl font-bold text-primary">{{ item.value }}</div>
            <div class="mt-1 text-sm text-muted-foreground">{{ item.label }}</div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
