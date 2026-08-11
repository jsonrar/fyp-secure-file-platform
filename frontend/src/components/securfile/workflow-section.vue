<script setup lang="ts">
import { KeyRound, Lock, Share2 } from 'lucide-vue-next'
import { RouterLink } from 'vue-router'

const steps = [
  {
    icon: Lock,
    step: '01',
    title: 'Encrypt locally',
    description: 'Files are encrypted before they leave your browser, so plaintext never has to sit on the server.',
  },
  {
    icon: KeyRound,
    step: '02',
    title: 'Hold your own keys',
    description: 'Generate a strong key or bring your own password. Access depends on the key, not just an account.',
  },
  {
    icon: Share2,
    step: '03',
    title: 'Share with control',
    description: 'Send encrypted files to teammates, then review access records and keep collaboration auditable.',
  },
]
</script>

<template>
  <section class="py-20 md:py-28">
    <div class="container mx-auto px-4">
      <div class="mb-14 text-center">
        <p class="mb-3 text-xs font-semibold uppercase tracking-[0.32em] text-primary">How it works</p>
        <h2 class="mb-4 text-3xl font-bold text-foreground md:text-4xl">From file to trusted share</h2>
        <p class="mx-auto max-w-2xl text-pretty text-muted-foreground">
          A short path designed for coursework, research, and team handoff — without turning security into extra homework.
        </p>
      </div>

      <div class="mx-auto grid max-w-6xl gap-6 md:grid-cols-3">
        <article v-for="item in steps" :key="item.step" class="rounded-2xl border border-border bg-card p-7">
          <div class="mb-6 flex items-center justify-between">
            <div class="rounded-xl bg-primary/10 p-3">
              <component :is="item.icon" class="h-6 w-6 text-primary" />
            </div>
            <span class="text-sm font-semibold tracking-[0.2em] text-muted-foreground">{{ item.step }}</span>
          </div>
          <h3 class="text-xl font-semibold text-foreground">{{ item.title }}</h3>
          <p class="mt-3 text-sm leading-relaxed text-muted-foreground">{{ item.description }}</p>
        </article>
      </div>

      <div class="mx-auto mt-16 flex max-w-6xl flex-col items-start justify-between gap-6 rounded-2xl border border-border bg-card px-8 py-10 md:flex-row md:items-center">
        <div>
          <h3 class="text-2xl font-semibold text-foreground">Ready to protect a file?</h3>
          <p class="mt-2 max-w-xl text-muted-foreground">Open the product workspace and run the same encrypt-and-share flow the team built for this platform.</p>
        </div>
        <RouterLink to="/upload" class="inline-flex h-11 shrink-0 items-center rounded-md bg-primary px-6 text-primary-foreground transition-colors hover:bg-primary/90">
          Go to Product
        </RouterLink>
      </div>
    </div>
  </section>
</template>
