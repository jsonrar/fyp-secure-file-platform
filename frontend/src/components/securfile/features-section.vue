<script setup lang="ts">
import { FileCheck, Key, Settings, Share2, ShieldCheck, Upload } from 'lucide-vue-next'
import type { Component } from 'vue'

interface FeatureItem {
  icon: Component
  title: string
  description: string
}

const features: FeatureItem[] = [
  {
    icon: Upload,
    title: 'File Upload',
    description:
      'Drag and drop or click to add files of any type, up to 500 MB each. Several files can be encrypted and uploaded in one go.',
  },
  {
    icon: Key,
    title: 'Key Generation',
    description:
      'Your browser makes a fresh random key for every file and seals it with your own public key. The server never sees it.',
  },
  {
    icon: ShieldCheck,
    title: 'Strong Encryption',
    description:
      'AES-256-GCM by default, or AES-128/192-GCM and ChaCha20-Poly1305: authenticated encryption, so a change is detected, not just hidden.',
  },
  {
    icon: Share2,
    title: 'Secure Sharing',
    description:
      'Share with a named account by re-sealing the file key for them. No public links to leak, and access can be revoked at any time.',
  },
  {
    icon: FileCheck,
    title: 'Integrity Verification',
    description:
      'Every download is checked against its authentication tag and SHA-256 fingerprint, and a daily scan checks every stored file.',
  },
  {
    icon: Settings,
    title: 'File Management',
    description:
      'Search, sort into folders, download and decrypt, see who opened a file, and delete what you no longer need.',
  },
]

const splitIndex = Math.ceil(features.length / 2)
const firstRow = features.slice(0, splitIndex)
const secondRow = features.slice(splitIndex)
</script>

<template>
  <section id="features" class="bg-transparent py-20">
    <div class="container mx-auto px-4">
      <div class="mb-16 text-center">
        <h2 class="mb-4 text-3xl font-bold text-foreground md:text-4xl">Core Features</h2>
        <p class="mx-auto max-w-2xl text-pretty text-muted-foreground">
          Everything is encrypted in your browser first, so the server only ever stores what it cannot read
        </p>
      </div>

      <div class="mx-auto max-w-6xl space-y-8">
        <!-- Three equal groups cover the viewport even at the one-group loop boundary.
             Keep the trailing gap inside each group so every seam has the same spacing. -->
        <div class="marquee-lane overflow-hidden [mask-image:linear-gradient(to_right,transparent,black_8%,black_92%,transparent)]">
          <div class="marquee-track marquee-right">
            <div
              v-for="copy in 3"
              :key="`row-1-copy-${copy}`"
              class="marquee-group"
              :aria-hidden="copy > 1 ? true : undefined"
            >
              <article
                v-for="feature in firstRow"
                :key="`row-1-${copy}-${feature.title}`"
                class="feature-card group"
              >
                <div class="mb-3 w-fit rounded-2xl bg-primary/10 p-3 transition-colors group-hover:bg-primary/20">
                  <component :is="feature.icon" class="h-6 w-6 text-primary" />
                </div>
                <h3 class="mb-2 font-semibold text-foreground">{{ feature.title }}</h3>
                <p class="text-sm leading-relaxed text-muted-foreground">{{ feature.description }}</p>
              </article>
            </div>
          </div>
        </div>

        <div class="marquee-lane overflow-hidden [mask-image:linear-gradient(to_right,transparent,black_8%,black_92%,transparent)]">
          <div class="marquee-track marquee-left">
            <div
              v-for="copy in 3"
              :key="`row-2-copy-${copy}`"
              class="marquee-group"
              :aria-hidden="copy > 1 ? true : undefined"
            >
              <article
                v-for="feature in secondRow"
                :key="`row-2-${copy}-${feature.title}`"
                class="feature-card group"
              >
                <div class="mb-3 w-fit rounded-2xl bg-primary/10 p-3 transition-colors group-hover:bg-primary/20">
                  <component :is="feature.icon" class="h-6 w-6 text-primary" />
                </div>
                <h3 class="mb-2 font-semibold text-foreground">{{ feature.title }}</h3>
                <p class="text-sm leading-relaxed text-muted-foreground">{{ feature.description }}</p>
              </article>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.marquee-lane {
  /* Room above/below so hover lift + shadow are not clipped by overflow:hidden */
  padding-block: 1.25rem;
}

.marquee-track {
  display: flex;
  width: max-content;
  will-change: transform;
}

.marquee-group {
  display: flex;
  flex-shrink: 0;
  gap: 1.5rem;
  /* Trailing gap matches card gap so the loop seam is identical to every other gap. */
  padding-inline-end: 1.5rem;
}

.marquee-left {
  animation: marquee-left 40s linear infinite;
}

.marquee-right {
  animation: marquee-right 40s linear infinite;
}

.marquee-lane:hover .marquee-track {
  animation-play-state: paused;
}

.feature-card {
  min-width: 320px;
  max-width: 320px;
  flex-shrink: 0;
  border-radius: 1.5rem;
  border: 1px solid color-mix(in oklab, var(--color-border) 88%, transparent);
  background-color: color-mix(in oklab, var(--color-card) 92%, transparent);
  padding: 1.5rem;
  box-shadow: 0 10px 28px color-mix(in oklab, var(--color-foreground) 5%, transparent);
  transition:
    border-color 0.25s ease,
    box-shadow 0.25s ease,
    transform 0.25s ease;
}

.feature-card:hover {
  border-color: color-mix(in oklab, var(--color-primary) 45%, transparent);
  box-shadow: 0 8px 22px color-mix(in oklab, var(--color-foreground) 6%, transparent);
  transform: translateY(-4px);
}

@keyframes marquee-left {
  from {
    transform: translate3d(0, 0, 0);
  }
  to {
    transform: translate3d(calc(-100% / 3), 0, 0);
  }
}

@keyframes marquee-right {
  from {
    transform: translate3d(calc(-100% / 3), 0, 0);
  }
  to {
    transform: translate3d(0, 0, 0);
  }
}

@media (max-width: 768px) {
  .marquee-left,
  .marquee-right {
    animation-duration: 28s;
  }

  .feature-card {
    min-width: 280px;
    max-width: 280px;
    border-radius: 1.35rem;
  }
}

@media (prefers-reduced-motion: reduce) {
  .marquee-left,
  .marquee-right {
    animation: none;
  }

  .marquee-track {
    transform: none !important;
    width: 100%;
  }

  .marquee-group[aria-hidden="true"] {
    display: none;
  }

  .marquee-group {
    width: 100%;
    flex-wrap: wrap;
    justify-content: center;
    padding-inline-end: 0;
  }

  .feature-card {
    min-width: 0;
    width: 100%;
  }

  .marquee-lane {
    mask-image: none;
  }
}
</style>
