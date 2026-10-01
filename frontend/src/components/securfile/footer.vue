<script setup lang="ts">
import { ArrowUp, FileCheck2, LockKeyhole, Mail, ServerOff, Users } from 'lucide-vue-next'
import { RouterLink } from 'vue-router'
import SecureViewMark from '@/components/brand/SecureViewMark.vue'

/**
 * The site footer. Every link goes to a page that exists: it used to list Privacy Policy, Terms of
 * Service, GitHub, X and Discord, all pointing at "#", so a click landed wherever the router sent
 * an empty hash. The first column mirrors the header, in the same order.
 */
const productLinks = [
  { label: 'Product', to: '/#features' },
  { label: 'How it works', to: '/how-it-works' },
  { label: 'Help', to: '/help' },
  { label: 'Education', to: '/education' },
  { label: 'Contact us', to: '/team' },
]
const learnLinks = [
  { label: 'Animated explainer', to: '/how-it-works' },
  { label: 'Walkthrough videos', to: '/help#videos' },
  { label: 'Picture guide', to: '/#how-it-works' },
  { label: 'Algorithm explorer', to: '/education' },
]
const promises = [
  { icon: LockKeyhole, text: 'Encrypted in your browser, before upload' },
  { icon: ServerOff, text: 'The server holds no key it can use to read your files' },
  { icon: FileCheck2, text: 'Every download checked for tampering' },
]
const FEEDBACK = 'mailto:swen0027@student.monash.edu?subject=%5BSecureView%5D%20Feedback'

function backToTop() {
  window.scrollTo({ top: 0, behavior: 'smooth' })
}
</script>

<template>
  <footer class="border-t border-border bg-card/50">
    <div class="container mx-auto px-4 py-14">
      <div class="grid gap-10 md:grid-cols-12">
        <div class="md:col-span-5">
          <RouterLink
            to="/"
            class="mb-4 inline-flex w-fit items-center text-foreground"
            aria-label="SecureView home"
          >
            <SecureViewMark variant="logo" class="h-8" />
          </RouterLink>
          <p class="max-w-md text-sm leading-relaxed text-muted-foreground">
            End-to-end encrypted file sharing. Your files are encrypted on your own device, shared by
            re-sealing a key for one named person, and stored as ciphertext the server cannot read.
          </p>
          <ul class="mt-5 space-y-2.5">
            <li v-for="item in promises" :key="item.text" class="flex items-center gap-2.5 text-sm text-foreground">
              <span class="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                <component :is="item.icon" class="h-4 w-4" />
              </span>
              {{ item.text }}
            </li>
          </ul>
        </div>

        <nav class="md:col-span-2 md:col-start-7" aria-label="Footer: product">
          <h4 class="mb-3 text-sm font-semibold text-foreground">Product</h4>
          <ul class="text-sm">
            <li v-for="link in productLinks" :key="link.label">
              <RouterLink :to="link.to" class="inline-flex min-h-9 items-center text-muted-foreground transition-colors hover:text-foreground">{{ link.label }}</RouterLink>
            </li>
          </ul>
        </nav>

        <nav class="md:col-span-2" aria-label="Footer: learn">
          <h4 class="mb-3 text-sm font-semibold text-foreground">Learn</h4>
          <ul class="text-sm">
            <li v-for="link in learnLinks" :key="link.label">
              <RouterLink :to="link.to" class="inline-flex min-h-9 items-center text-muted-foreground transition-colors hover:text-foreground">{{ link.label }}</RouterLink>
            </li>
          </ul>
        </nav>

        <div class="md:col-span-2">
          <h4 class="mb-3 text-sm font-semibold text-foreground">The project</h4>
          <p class="text-sm leading-relaxed text-muted-foreground">
            A Monash University final-year project (FIT3161/FIT3162) by team MCS21, supervised by
            Dr. Asad Malik.
          </p>
          <RouterLink to="/team" class="mt-3 inline-flex min-h-9 items-center gap-1.5 text-sm font-medium text-primary hover:underline">
            <Users class="h-4 w-4" /> Meet the team
          </RouterLink>
        </div>
      </div>

      <div class="mt-12 flex flex-col items-center justify-between gap-3 border-t border-border pt-6 sm:flex-row">
        <p class="text-sm text-muted-foreground">© 2026 SecureView · Team MCS21, Monash University</p>
        <div class="flex items-center gap-1 text-sm">
          <a :href="FEEDBACK" class="inline-flex min-h-10 items-center gap-1.5 rounded-md px-2.5 text-muted-foreground transition-colors hover:text-foreground">
            <Mail class="h-4 w-4" /> Send feedback
          </a>
          <button type="button" class="inline-flex min-h-10 items-center gap-1.5 rounded-md px-2.5 text-muted-foreground transition-colors hover:text-foreground" @click="backToTop">
            <ArrowUp class="h-4 w-4" /> Back to top
          </button>
        </div>
      </div>
    </div>
  </footer>
</template>
