<script setup lang="ts">
import { ArrowRight, CircleHelp, Images } from 'lucide-vue-next'
import { RouterLink } from 'vue-router'
import SoftwareGuide from '@/components/education/SoftwareGuide.vue'
</script>

<template>
  <section class="py-16 md:py-24">
    <div class="container mx-auto px-4">
      <div class="mb-12 mx-auto max-w-3xl text-center">
        <div class="mb-5 inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/10 px-4 py-2">
          <!-- <CircleHelp class="h-4 w-4 text-primary" /> -->
          <span class="text-sm font-medium text-primary">Product Help</span>
        </div>
        <h1 class="mb-4 text-balance text-3xl font-bold text-foreground md:text-5xl">How to Use SecureView</h1>
        <p class="text-pretty text-lg text-muted-foreground">
          Start with the annotated screenshot guide on the home page, then come back here for longer video walkthroughs when they ship.
        </p>
      </div>

      <div class="mx-auto mb-10 max-w-6xl rounded-3xl border border-border bg-card p-6 md:flex md:items-center md:justify-between md:gap-8 md:p-8">
        <div class="flex items-start gap-4">
          <div class="rounded-2xl bg-primary/10 p-3 text-primary">
            <Images class="h-6 w-6" />
          </div>
          <div>
            <h2 class="text-xl font-semibold text-foreground">Picture guide: your first secure share</h2>
            <p class="mt-2 max-w-2xl text-sm leading-relaxed text-muted-foreground">
              Six real-interface screenshots under How it works — choose a file, encrypt, share, unlock, and download — with blue numbered outlines on the controls to click.
            </p>
          </div>
        </div>
        <RouterLink
          to="/#how-it-works"
          class="mt-5 inline-flex h-11 shrink-0 items-center gap-2 rounded-full bg-primary px-6 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90 md:mt-0"
        >
          Open the guide
          <ArrowRight class="h-4 w-4" />
        </RouterLink>
      </div>

      <div class="mx-auto max-w-6xl">
        <div class="mb-6">
          <p class="text-xs font-semibold uppercase tracking-[0.22em] text-primary">Videos</p>
          <h2 class="mt-2 text-2xl font-semibold text-foreground">Longer walkthrough clips</h2>
          <p class="mt-2 text-sm text-muted-foreground">Coming next — placeholders stay here until the footage is ready.</p>
        </div>
        <SoftwareGuide />
      </div>
    </div>
  </section>
</template>
