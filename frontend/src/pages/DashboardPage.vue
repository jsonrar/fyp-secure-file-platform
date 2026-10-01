<script setup lang="ts">
import { ArrowRight } from 'lucide-vue-next'
import { RouterLink } from 'vue-router'

import HeroSection from '@/components/securfile/hero-section.vue'
import FeaturesSection from '@/components/securfile/features-section.vue'
import WorkflowSection from '@/components/securfile/workflow-section.vue'
import SecurityStory from '@/components/explainers/SecurityStory.vue'
import WhySecureView from '@/components/explainers/WhySecureView.vue'
</script>

<template>
  <HeroSection />
  <FeaturesSection />

  <!-- What happens to a file, animated; then why that beats ordinary cloud storage. -->
  <section id="security-story" class="py-20" aria-labelledby="story-heading">
    <div class="container mx-auto max-w-6xl px-4">
      <div class="mx-auto mb-10 max-w-3xl text-center">
        <p class="mb-3 text-xs font-semibold uppercase tracking-[0.32em] text-primary">Under the hood</p>
        <h2 id="story-heading" class="text-balance text-3xl font-bold tracking-tight text-foreground md:text-4xl">
          What happens to your file
        </h2>
        <p class="mx-auto mt-4 max-w-2xl text-pretty text-muted-foreground">
          Encrypted in your browser, stored as noise, shared by re-sealing a key, and checked on the way out.
        </p>
      </div>
      <SecurityStory compact />
    </div>
  </section>

  <section class="bg-secondary/30 py-20" aria-labelledby="why-home-heading">
    <div class="container mx-auto max-w-6xl px-4">
      <div class="mx-auto mb-10 max-w-3xl text-center">
        <p class="mb-3 text-xs font-semibold uppercase tracking-[0.32em] text-primary">Why SecureView</p>
        <h2 id="why-home-heading" class="text-balance text-3xl font-bold tracking-tight text-foreground md:text-4xl">
          Compared with ordinary cloud storage
        </h2>
      </div>
      <WhySecureView />
      <div class="mt-8 text-center">
        <RouterLink to="/how-it-works" class="inline-flex items-center gap-1.5 text-sm font-medium text-primary hover:underline">
          The full explainer and a four-step quick start <ArrowRight class="h-4 w-4" />
        </RouterLink>
      </div>
    </div>
  </section>

  <WorkflowSection />
</template>
