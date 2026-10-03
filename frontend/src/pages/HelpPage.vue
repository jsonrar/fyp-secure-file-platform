<script setup lang="ts">
import { ArrowRight, Images, PlayCircle, Sparkles } from 'lucide-vue-next'
import { RouterLink } from 'vue-router'
import SoftwareGuide from '@/components/education/SoftwareGuide.vue'
</script>

<template>
  <section class="product-page">
    <div class="container relative mx-auto max-w-6xl px-4">
      <div class="product-heading">
        <div class="mb-5 inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/10 px-4 py-2">
          <span class="text-sm font-medium text-primary">Product Help</span>
        </div>
        <h1 class="mb-4 text-balance text-3xl font-bold text-foreground md:text-5xl">How to Use SecureView</h1>
        <p class="text-pretty text-lg text-muted-foreground">
          Three ways in: an animated explainer of how your files stay private, short videos of the real product,
          and a picture guide you can follow click by click.
        </p>
      </div>

      <div class="mx-auto mb-12 grid max-w-6xl gap-4 md:grid-cols-3">
        <RouterLink
          to="/how-it-works"
          class="group rounded-2xl border border-border bg-card p-5 transition-colors hover:border-primary/50"
        >
          <div class="mb-3 w-fit rounded-xl bg-primary/10 p-2.5 text-primary"><Sparkles class="h-5 w-5" /></div>
          <h2 class="font-semibold text-foreground">How it works, animated</h2>
          <p class="mt-1.5 text-sm text-muted-foreground">
            Follow one file from Alice to Bob, see why a server breach exposes nothing, and get a four-step quick start.
          </p>
          <span class="mt-3 inline-flex items-center gap-1 text-sm font-medium text-primary">
            Open the explainer <ArrowRight class="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
          </span>
        </RouterLink>
        <a href="#videos" class="group rounded-2xl border border-border bg-card p-5 transition-colors hover:border-primary/50">
          <div class="mb-3 w-fit rounded-xl bg-primary/10 p-2.5 text-primary"><PlayCircle class="h-5 w-5" /></div>
          <h2 class="font-semibold text-foreground">Walkthrough videos</h2>
          <p class="mt-1.5 text-sm text-muted-foreground">
            About a minute each, recorded from the real product: encrypt and upload, then share and open.
          </p>
          <span class="mt-3 inline-flex items-center gap-1 text-sm font-medium text-primary">
            Watch below <ArrowRight class="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
          </span>
        </a>
        <RouterLink
          to="/#how-it-works"
          class="group rounded-2xl border border-border bg-card p-5 transition-colors hover:border-primary/50"
        >
          <div class="mb-3 w-fit rounded-xl bg-primary/10 p-2.5 text-primary"><Images class="h-5 w-5" /></div>
          <h2 class="font-semibold text-foreground">Picture guide</h2>
          <p class="mt-1.5 text-sm text-muted-foreground">
            Six real-interface screenshots — choose, encrypt, share, unlock, download — with the controls outlined.
          </p>
          <span class="mt-3 inline-flex items-center gap-1 text-sm font-medium text-primary">
            Open the guide <ArrowRight class="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
          </span>
        </RouterLink>
      </div>

      <div id="videos" class="mx-auto max-w-6xl scroll-mt-24">
        <div class="mb-6">
          <p class="text-xs font-semibold uppercase tracking-[0.22em] text-primary">Videos</p>
          <h2 class="mt-2 text-2xl font-semibold text-foreground">Watch it work</h2>
          <p class="mt-2 text-sm text-muted-foreground">
            Recorded from the real product with made-up accounts (Sam and Alex). Every step is captioned on screen and listed beside the video.
          </p>
        </div>
        <SoftwareGuide />
      </div>
    </div>
  </section>
</template>
