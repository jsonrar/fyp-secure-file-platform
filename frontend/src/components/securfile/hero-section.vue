<script setup lang="ts">
import { ArrowRight, ChevronDown, Sparkles } from 'lucide-vue-next'
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import type { CSSProperties } from 'vue'
import { RouterLink } from 'vue-router'

const highlights = [
  { value: 'AES & RSA', label: 'Encryption' },
  { value: '100%', label: 'Local Encryption' },
  { value: 'Easy Use', label: 'Architecture' },
  { value: '100GB', label: 'File Size' },
]

const TITLE_END = 0.42
const INTRO_IN = 0.18
const INTRO_READY = 0.52

const trackRef = ref<HTMLElement | null>(null)
const progress = ref(0)
let frame = 0

function clamp(value: number, min = 0, max = 1) {
  return Math.min(max, Math.max(min, value))
}

function updateProgress() {
  const track = trackRef.value
  if (!track) return
  const total = track.offsetHeight - window.innerHeight
  if (total <= 0) {
    progress.value = 0
    return
  }
  progress.value = clamp(-track.getBoundingClientRect().top / total)
}

function onFrame() {
  frame = 0
  updateProgress()
}

function requestFrame() {
  if (frame) return
  frame = window.requestAnimationFrame(onFrame)
}

const titleLeave = computed(() => clamp(progress.value / TITLE_END))
const titleStyle = computed((): CSSProperties => {
  const t = titleLeave.value
  return {
    opacity: String(1 - t),
    transform: `translate3d(0, ${-t * 56}px, ${-t * 480}px) scale(${1 - t * 0.28})`,
    filter: `blur(${t * 8}px)`,
    pointerEvents: t > 0.85 ? 'none' : 'auto',
  }
})

const introEnter = computed(() => clamp((progress.value - INTRO_IN) / (INTRO_READY - INTRO_IN)))
const introStyle = computed((): CSSProperties => {
  const t = introEnter.value
  return {
    opacity: String(t),
    transform: `translate3d(0, ${(1 - t) * 48}px, ${(1 - t) * 280}px) scale(${0.84 + t * 0.16})`,
    pointerEvents: t > 0.4 ? 'auto' : 'none',
  }
})

onMounted(() => {
  updateProgress()
  window.addEventListener('scroll', requestFrame, { passive: true })
  window.addEventListener('resize', requestFrame)
})

onBeforeUnmount(() => {
  window.removeEventListener('scroll', requestFrame)
  window.removeEventListener('resize', requestFrame)
  if (frame) window.cancelAnimationFrame(frame)
})
</script>

<template>
  <section ref="trackRef" class="home-scroll-track relative">
    <div class="home-scene sticky top-0 h-svh overflow-hidden">
      <div class="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_50%_30%,color-mix(in_oklab,var(--primary)_16%,transparent),transparent_58%)]" />

      <div class="home-perspective relative mx-auto flex h-full items-center justify-center">
        <div class="home-title absolute inset-0 z-20 flex flex-col items-center justify-center px-4 text-center" :style="titleStyle">
          <p class="mb-5 text-xs font-semibold uppercase tracking-[0.35em] text-primary">SecureView</p>
          <h1 class="max-w-5xl text-5xl font-bold leading-[0.92] tracking-tight text-foreground sm:text-7xl md:text-8xl lg:text-[7.5rem]">
            <span class="block">Encryption</span>
            <span class="block text-primary">and</span>
            <span class="block">Sharing</span>
          </h1>
          <div class="mt-12 flex flex-col items-center gap-2 text-muted-foreground" :style="{ opacity: String(1 - titleLeave * 2) }">
            <span class="text-xs uppercase tracking-[0.28em]">Scroll to explore</span>
            <ChevronDown class="h-5 w-5 animate-bounce" />
          </div>
        </div>

        <div class="home-intro relative z-10 flex h-full w-full flex-col items-center justify-center px-4 pt-28" :style="introStyle">
          <div class="inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/10 px-4 py-2 mb-6">
            <Sparkles class="h-4 w-4 text-primary" />
            <span class="text-sm font-medium text-primary">Encrypted File Sharing Platform</span>
          </div>
          <h2 class="mx-auto mb-6 max-w-4xl text-center text-3xl font-bold leading-tight text-foreground md:text-5xl lg:text-6xl">
            Securely Encrypt and Share Your Sensitive Files
          </h2>
          <p class="mx-auto mb-10 max-w-2xl text-center text-base text-muted-foreground md:text-xl">
            Protect your files with powerful encryption technology. Generate unique keys, share securely, and manage your encrypted files with ease.
          </p>
          <div class="flex flex-col items-center justify-center gap-4 sm:flex-row">
            <RouterLink to="/upload" class="inline-flex h-11 items-center gap-2 rounded-md bg-primary px-8 text-primary-foreground transition-colors hover:bg-primary/90">
              Encrypt Your Files
              <ArrowRight class="h-4 w-4" />
            </RouterLink>
            <RouterLink to="/education" class="inline-flex h-11 items-center rounded-md border border-border px-8 text-foreground transition-colors hover:bg-secondary">
              Learn More
            </RouterLink>
          </div>
          <div class="mt-16 grid max-w-3xl grid-cols-2 gap-8 md:grid-cols-4">
            <div v-for="item in highlights" :key="item.value" class="text-center">
              <div class="text-3xl font-bold text-primary">{{ item.value }}</div>
              <div class="mt-1 text-sm text-muted-foreground">{{ item.label }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.home-scroll-track {
  height: 220vh;
}

.home-perspective {
  perspective: 1600px;
  perspective-origin: 50% 46%;
  transform-style: preserve-3d;
}

.home-title,
.home-intro {
  transform-style: preserve-3d;
  will-change: transform, opacity;
}

@media (prefers-reduced-motion: reduce) {
  .home-scroll-track {
    height: auto;
  }

  .home-scene {
    position: relative;
    height: auto;
    overflow: visible;
  }

  .home-title,
  .home-intro {
    position: static;
    transform: none !important;
    opacity: 1 !important;
    filter: none !important;
    pointer-events: auto !important;
    padding-top: 5rem;
    padding-bottom: 3rem;
  }
}
</style>
