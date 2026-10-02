<script setup lang="ts">
import { computed, ref } from 'vue'
import { Clapperboard } from 'lucide-vue-next'

/**
 * The Help page's videos, recorded from the real product by `scripts/record-walkthroughs.mjs`
 * against a local stack with made-up accounts (Sam and Alex). The captions are burned into the
 * video; the same steps are listed under it as text, for anyone who cannot watch or hear it.
 */
const guides = [
  {
    id: 'how-it-works',
    tag: 'Animation',
    title: 'What happens to your file',
    summary: 'One file followed from Alice to Bob: encrypted in the browser, stored as noise, shared, opened, and protected from tampering.',
    videoSrc: '/videos/how-it-works.mp4',
    poster: '/videos/how-it-works.jpg',
    steps: [
      'Alice picks a file; it is still only on her computer.',
      'Her browser encrypts it with a new random key.',
      'The key is sealed with her public key, plus an offline recovery copy.',
      'Only ciphertext and sealed keys reach the server.',
      'Sharing re-seals the key for Bob; the file is not copied.',
      'Bob opens it with his own passphrase, and it is verified.',
      'A changed byte is caught and the original is restored from backup.',
    ],
  },
  {
    id: 'encrypt-upload',
    tag: 'Walkthrough',
    title: 'Encrypt & upload a file',
    summary: 'Sign in, choose a file, pick the cipher, and encrypt it in the browser so only ciphertext is uploaded.',
    videoSrc: '/videos/encrypt-upload.mp4',
    poster: '/videos/encrypt-upload.jpg',
    steps: [
      'Sign in with your password (it only signs you in).',
      'Open Upload and choose a file.',
      'Keep AES-256-GCM or pick another authenticated cipher.',
      'Press Start Encryption: the file is encrypted before it is sent.',
      'In My Files the sizes match — the tag is stored separately.',
      'Encrypted preview shows what the server holds: random-looking bytes.',
    ],
  },
  {
    id: 'share-access',
    tag: 'Walkthrough',
    title: 'Share securely with another account',
    summary: 'Share with a named account by re-sealing the key, then see the recipient decrypt it with their own passphrase and file it in a folder of their own.',
    videoSrc: '/videos/share-open.mp4',
    poster: '/videos/share-open.jpg',
    steps: [
      'In My Files, press Share on the file.',
      'Unlock your key with your encryption passphrase (it stays in the browser).',
      'Enter the recipient’s username and press Share.',
      'The recipient signs in and finds it under Shared with me.',
      'Download and decrypt, with the recipient’s own passphrase.',
      'The tag and SHA-256 match, so it is exactly the uploaded file.',
      'The recipient files it in a private folder; the owner’s folders are unaffected.',
    ],
  },
]

const activeId = ref(guides[0]!.id)
const active = computed(() => guides.find((g) => g.id === activeId.value)!)
</script>

<template>
  <div class="space-y-6">
    <div class="flex flex-wrap gap-2" role="tablist" aria-label="Videos">
      <button
        v-for="guide in guides"
        :key="guide.id"
        type="button"
        role="tab"
        :aria-selected="activeId === guide.id"
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

    <article class="overflow-hidden rounded-xl border border-border bg-card" data-testid="help-video">
      <div class="border-b border-border px-5 py-4">
        <p class="mb-2 text-xs font-semibold uppercase tracking-[0.22em] text-primary">{{ active.tag }}</p>
        <h3 class="text-xl font-bold text-foreground">{{ active.title }}</h3>
        <p class="mt-2 max-w-2xl text-sm text-muted-foreground">{{ active.summary }}</p>
      </div>

      <div class="grid gap-0 lg:grid-cols-[minmax(0,1fr)_18rem]">
        <div class="bg-black/90">
          <video
            :key="active.id"
            class="aspect-video h-auto w-full"
            controls
            playsinline
            preload="metadata"
            :src="active.videoSrc"
            :poster="active.poster"
            :aria-label="active.title"
          />
        </div>
        <div class="border-t border-border p-5 lg:border-l lg:border-t-0">
          <p class="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">In this video</p>
          <ol class="mt-3 space-y-2 text-sm text-foreground">
            <li v-for="(step, i) in active.steps" :key="step" class="flex gap-2">
              <span class="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-semibold text-primary">{{ i + 1 }}</span>
              <span>{{ step }}</span>
            </li>
          </ol>
        </div>
      </div>
    </article>
  </div>
</template>
