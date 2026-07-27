<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ShieldCheck, Users, FileIcon } from 'lucide-vue-next'
import { recoveryApi } from '@/api/recovery_api'
import { unwrapData } from '@/api/types'

const requests = ref<unknown[]>([])
const message = ref('')

onMounted(async () => {
  try {
    const res = await recoveryApi.listRequests()
    const data = unwrapData(res) as { requests?: unknown[] }
    requests.value = data.requests ?? []
  } catch (error) {
    message.value = error instanceof Error ? error.message : 'Failed to load admin data'
  }
})
</script>

<template>
  <section class="py-20">
    <div class="container mx-auto px-4">
      <div class="text-center mb-12">
        <h1 class="text-3xl md:text-4xl font-bold text-foreground mb-4">Admin Panel</h1>
        <p class="text-muted-foreground max-w-2xl mx-auto">Manage recovery requests and platform administration tasks.</p>
      </div>

      <div class="max-w-4xl mx-auto grid md:grid-cols-3 gap-6 mb-8">
        <article class="rounded-xl border border-border bg-card p-6">
          <ShieldCheck class="h-6 w-6 text-primary mb-3" />
          <h2 class="font-semibold text-foreground">Security</h2>
          <p class="text-sm text-muted-foreground mt-2">AES-256-GCM encryption with RSA key wrapping.</p>
        </article>
        <article class="rounded-xl border border-border bg-card p-6">
          <Users class="h-6 w-6 text-primary mb-3" />
          <h2 class="font-semibold text-foreground">Recovery</h2>
          <p class="text-sm text-muted-foreground mt-2">{{ requests.length }} recovery requests loaded.</p>
        </article>
        <article class="rounded-xl border border-border bg-card p-6">
          <FileIcon class="h-6 w-6 text-primary mb-3" />
          <h2 class="font-semibold text-foreground">Files</h2>
          <p class="text-sm text-muted-foreground mt-2">Use the Files page to manage encrypted assets.</p>
        </article>
      </div>

      <div v-if="message" class="max-w-4xl mx-auto rounded-xl border border-border bg-card p-6 text-sm text-muted-foreground">
        {{ message }}
      </div>
    </div>
  </section>
</template>
