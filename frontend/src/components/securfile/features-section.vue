<script setup lang="ts">
import { FileCheck, Key, Settings, Share2, ShieldCheck, Upload } from 'lucide-vue-next'

const features = [
  {
    icon: Upload,
    title: 'File Upload',
    description:
      'Drag and drop or click to upload any file type. Batch processing supported for quick and convenient uploads.',
  },
  {
    icon: Key,
    title: 'Key Generation',
    description:
      'Automatically generate strong random keys or use custom passwords to protect your files securely.',
  },
  {
    icon: ShieldCheck,
    title: 'Strong Encryption',
    description: 'Uses AES-256 encryption standard to provide bank-level security protection.',
  },
  {
    icon: Share2,
    title: 'Secure Sharing',
    description:
      'Generate secure links to share encrypted files with others. Set access permissions and expiration times.',
  },
  {
    icon: FileCheck,
    title: 'Integrity Verification',
    description:
      "Use hash verification to ensure files haven't been tampered with or modified during transmission.",
  },
  {
    icon: Settings,
    title: 'File Management',
    description:
      'Easily manage all your encrypted files including viewing, downloading, and deletion operations.',
  },
]

const splitIndex = Math.ceil(features.length / 2)
const firstRow = features.slice(0, splitIndex)
const secondRow = features.slice(splitIndex)
</script>

<template>
  <section id="features" class="py-20 bg-transparent">
    <div class="container mx-auto px-4">
      <div class="mb-16 text-center">
        <h2 class="mb-4 text-3xl font-bold text-foreground md:text-4xl">Core Features</h2>
        <p class="mx-auto max-w-2xl text-pretty text-muted-foreground">
          Comprehensive file encryption solution to ensure your data is always secure and protected
        </p>
      </div>

      <div class="space-y-8">
        <div class="marquee-lane overflow-hidden [mask-image:linear-gradient(to_right,transparent,black_10%,black_90%,transparent)]">
          <div class="marquee-track marquee-right">
            <article
              v-for="(feature, index) in [...firstRow, ...firstRow]"
              :key="`row-1-${feature.title}-${index}`"
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

        <div class="marquee-lane overflow-hidden [mask-image:linear-gradient(to_right,transparent,black_10%,black_90%,transparent)]">
          <div class="marquee-track marquee-left">
            <article
              v-for="(feature, index) in [...secondRow, ...secondRow]"
              :key="`row-2-${feature.title}-${index}`"
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
  gap: 1.5rem;
}

.marquee-left {
  animation: marquee-left 30s linear infinite;
}

.marquee-right {
  animation: marquee-right 30s linear infinite;
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
    transform: translateX(0);
  }
  to {
    transform: translateX(-50%);
  }
}

@keyframes marquee-right {
  from {
    transform: translateX(-50%);
  }
  to {
    transform: translateX(0);
  }
}

@media (max-width: 768px) {
  .marquee-left,
  .marquee-right {
    animation-duration: 22s;
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
}
</style>
