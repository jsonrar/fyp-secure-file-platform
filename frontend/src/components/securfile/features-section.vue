<script setup lang="ts">
import { FileCheck, Key, Settings, Share2, ShieldCheck, Upload } from 'lucide-vue-next'

const features = [
  { icon: Upload, title: 'File Upload', description: 'Drag and drop or click to upload any file type. Batch processing supported for quick and convenient uploads.' },
  { icon: Key, title: 'Key Generation', description: 'Automatically generate strong random keys or use custom passwords to protect your files securely.' },
  { icon: ShieldCheck, title: 'Strong Encryption', description: 'Uses AES-256 encryption standard to provide bank-level security protection.' },
  { icon: Share2, title: 'Secure Sharing', description: 'Generate secure links to share encrypted files with others. Set access permissions and expiration times.' },
  { icon: FileCheck, title: 'Integrity Verification', description: 'Use hash verification to ensure files haven\'t been tampered with or modified during transmission.' },
  { icon: Settings, title: 'File Management', description: 'Easily manage all your encrypted files including viewing, downloading, and deletion operations.' },
]

const splitIndex = Math.ceil(features.length / 2)
const firstRow = features.slice(0, splitIndex)
const secondRow = features.slice(splitIndex)
</script>

<template>
  <section id="features" class="py-20 bg-transparent">
    <div class="container mx-auto px-4">
      <div class="text-center mb-16">
        <h2 class="text-3xl md:text-4xl font-bold text-foreground mb-4">Core Features</h2>
        <p class="text-muted-foreground max-w-2xl mx-auto text-pretty">Comprehensive file encryption solution to ensure your data is always secure and protected</p>
      </div>

      <div class="space-y-6">
        <div class="overflow-hidden [mask-image:linear-gradient(to_right,transparent,black_10%,black_90%,transparent)]">
          <div class="marquee-track marquee-right">
            <article
              v-for="(feature, index) in [...firstRow, ...firstRow]"
              :key="`row-1-${feature.title}-${index}`"
              class="feature-card"
            >
              <div class="p-3 rounded-lg bg-primary/10 w-fit mb-2 group-hover:bg-primary/20 transition-colors">
                <component :is="feature.icon" class="h-6 w-6 text-primary" />
              </div>
              <h3 class="text-foreground font-semibold mb-2">{{ feature.title }}</h3>
              <p class="text-sm text-muted-foreground">{{ feature.description }}</p>
            </article>
          </div>
        </div>

        <div class="overflow-hidden [mask-image:linear-gradient(to_right,transparent,black_10%,black_90%,transparent)]">
          <div class="marquee-track marquee-left">
            <article
              v-for="(feature, index) in [...secondRow, ...secondRow]"
              :key="`row-2-${feature.title}-${index}`"
              class="feature-card"
            >
              <div class="p-3 rounded-lg bg-primary/10 w-fit mb-2 group-hover:bg-primary/20 transition-colors">
                <component :is="feature.icon" class="h-6 w-6 text-primary" />
              </div>
              <h3 class="text-foreground font-semibold mb-2">{{ feature.title }}</h3>
              <p class="text-sm text-muted-foreground">{{ feature.description }}</p>
            </article>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
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

.feature-card {
  min-width: 320px;
  max-width: 320px;
  flex-shrink: 0;
  border-radius: 0.75rem;
  border: 1px solid var(--color-border);
  background-color: var(--color-card);
  padding: 1.5rem;
  transition: border-color 0.2s ease;
}

.feature-card:hover {
  border-color: color-mix(in oklab, var(--color-primary) 50%, transparent);
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
  }
}
</style>
