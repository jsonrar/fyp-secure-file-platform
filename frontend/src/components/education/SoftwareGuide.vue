<script setup lang="ts">
import { computed, ref } from 'vue'
import { Clapperboard } from 'lucide-vue-next'

/**
 * Software-usage videos for the Help page.
 * Set `videoSrc` when a walkthrough clip is ready.
 */
const guides = [
  {
    id: 'encrypt-upload',
    tag: 'Video',
    title: 'Encrypt & upload a file',
    summary: 'Pick a file in the browser, encrypt it locally, then upload only ciphertext.',
    videoSrc: '' as string,
  },
  {
    id: 'share-access',
    tag: 'Video',
    title: 'Share securely with another account',
    summary: 'Wrap the file key for a recipient and review access without exposing plaintext to the server.',
    videoSrc: '' as string,
  },
]

const activeId = ref(guides[0].id)
const active = computed(() => guides.find((g) => g.id === activeId.value)!)
const hasVideo = computed(() => Boolean(active.value.videoSrc))
</script>

<template>
  <div class="space-y-6">
    <div class="flex flex-wrap gap-2">
      <button
        v-for="guide in guides"
        :key="guide.id"
        type="button"
        class="inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-sm transition-colors"
        :class="
          activeId === guide.id
            ? 'border-primary bg-primary/10 text-foreground'
            : 'border-border bg-card text-muted-foreground hover:border-primary/40 hover:text-foreground'
        "
        @click="activeId = guide.id"
      >
        <Clapperboard class="h-3.5 w-3.5 text-primary" />
        <span>{{ guide.title }}</span>
        <span class="text-xs font-semibold uppercase tracking-[0.14em] text-primary/80">{{ guide.tag }}</span>
      </button>
    </div>

    <article class="rounded-xl border border-border bg-card overflow-hidden">
      <div class="px-5 py-4 border-b border-border">
        <p class="text-xs font-semibold uppercase tracking-[0.22em] text-primary mb-2">{{ active.tag }}</p>
        <h3 class="text-xl font-bold text-foreground">{{ active.title }}</h3>
        <p class="text-sm text-muted-foreground mt-2 max-w-2xl">{{ active.summary }}</p>
      </div>

      <div class="relative flex items-center justify-center aspect-[16/9] max-h-[26rem]">
        <video
          v-if="hasVideo"
          class="mx-auto h-full w-full max-w-full object-contain"
          controls
          playsinline
          :src="active.videoSrc"
          :aria-label="active.title"
        />
        <p v-else class="text-sm text-muted-foreground">Video demo still in development</p>
      </div>
    </article>
  </div>
</template>
