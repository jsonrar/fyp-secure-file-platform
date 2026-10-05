<script setup lang="ts">
import { ArrowRight } from 'lucide-vue-next'
import { RouterLink } from 'vue-router'
import { MAX_UPLOAD_BYTES } from '@/crypto/upload'
import { formatFileSize } from '@/api/types'
import { useAuthStore } from '@/stores/auth_store'

const auth = useAuthStore()

const maxUploadLabel = formatFileSize(MAX_UPLOAD_BYTES).replace(' ', '')

const highlights = [
  { value: 'In-browser', label: 'Encrypted before upload' },
  { value: 'AES · RSA', label: 'Standard ciphers' },
  { value: '0 Key', label: 'Readable by the server' },
  { value: maxUploadLabel, label: 'Per file' },
]
</script>

<template>
  <!-- Fill the first viewport so Core Features stays below the fold. -->
  <section class="relative flex min-h-svh items-center overflow-hidden py-24 md:py-28">

    <div class="container relative mx-auto px-4">
      <div class="mx-auto flex max-w-4xl flex-col items-center text-center">
        <div class="mb-6 inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/10 px-4 py-2">
          <span class="text-sm font-medium text-primary">End-to-end encrypted file sharing</span>
        </div>

        <h1 class="mb-6 max-w-4xl text-4xl font-bold tracking-tight text-foreground sm:text-5xl md:text-6xl">
          Share files
          <span class="text-primary">no server can read</span>
        </h1>

        <p class="mb-10 max-w-2xl text-base text-muted-foreground md:text-xl">
          Files are encrypted in your browser before they are uploaded, shared by re-sealing the key for a
          named person, and checked for tampering on the way back. The server only ever stores what it
          cannot read.
        </p>

        <div class="flex flex-col items-center justify-center gap-4 sm:flex-row">
          <!-- Signed out, /upload only redirects to sign in, so the first step is an account. -->
          <RouterLink
            :to="auth.isAuthed ? '/upload' : '/register'"
            class="inline-flex h-11 items-center gap-2 rounded-full bg-primary px-8 text-primary-foreground transition-colors hover:bg-primary/90"
          >
            {{ auth.isAuthed ? 'Encrypt a file' : 'Get started' }}
            <ArrowRight class="h-4 w-4" />
          </RouterLink>
          <RouterLink
            to="/how-it-works"
            class="inline-flex h-11 items-center rounded-full border border-border px-8 text-foreground transition-colors hover:bg-secondary"
          >
            See how it works
          </RouterLink>
        </div>

        <div class="mt-16 grid w-full max-w-4xl grid-cols-2 gap-x-3 gap-y-8 md:grid-cols-4">
          <div v-for="item in highlights" :key="item.value" class="text-center">
            <div class="text-2xl font-bold text-primary md:text-3xl">{{ item.value }}</div>
            <div class="mt-1 whitespace-nowrap text-xs text-muted-foreground sm:text-sm">{{ item.label }}</div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
