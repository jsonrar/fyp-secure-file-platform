<script setup lang="ts">
/**
 * The home page's feature overview. It replaces the old scrolling wall of icon cards: the same
 * information, said as the three things the product does, each with the real artefact it produces.
 * Keep id="features": the header and footer "Product" links point at it.
 */
import { proof } from '@/data/proof'
const alsoIncluded = [
  'Folders and search',
  'Who opened a file',
  'Six ciphers',
  'Daily integrity scan',
  'Revoke access any time',
  'English and 简体中文',
]
</script>

<template>
  <section id="features" class="scroll-mt-24 bg-background" aria-labelledby="moves-heading">
    <div class="border-y border-border bg-card">
      <div class="container mx-auto px-4 py-12">
        <ul class="grid grid-cols-2 gap-x-6 gap-y-8 lg:grid-cols-4" data-testid="home-proof">
          <li v-for="item in proof" :key="item.value" class="flex flex-col gap-2">
            <span class="text-4xl font-semibold tracking-[-0.03em] text-foreground md:text-5xl">{{ item.value }}</span>
            <span class="text-sm leading-relaxed text-muted-foreground">{{ item.label }}</span>
          </li>
        </ul>
        <p class="mt-8 font-mono text-xs text-muted-foreground">From our own test runs on the live site; the reports are in the project documentation.</p>
      </div>
    </div>

    <div class="container mx-auto px-4 py-24">
      <div class="mb-12 flex flex-col items-center gap-4 text-center">
        <p class="font-mono text-xs uppercase tracking-[0.14em] text-muted-foreground">How it works</p>
        <h2 id="moves-heading" class="text-balance text-4xl font-semibold leading-[1.1] md:text-5xl">
          Three moves. The server is trusted with none of them.
        </h2>
      </div>
      <div class="grid gap-6 md:grid-cols-3">
        <article class="flex flex-col gap-5 rounded-xl border border-border bg-card p-7">
          <span class="font-mono text-xs text-muted-foreground">01 — Seal</span>
          <h3 class="text-2xl font-semibold">Encrypted before it leaves</h3>
          <p class="leading-relaxed text-muted-foreground">
            A new random key for every file, up to 500 MB. Your passphrase unlocks your private key here, in
            the browser, through Argon2id, and never travels.
          </p>
          <p class="mt-auto rounded-lg bg-secondary px-4 py-3 font-mono text-xs">
            key → RSA-OAEP → <span class="text-success">sealed ×2</span>
          </p>
        </article>
        <article class="flex flex-col gap-5 rounded-xl border border-border bg-card p-7">
          <span class="font-mono text-xs text-muted-foreground">02 — Share</span>
          <h3 class="text-2xl font-semibold">Only to a key you have checked</h3>
          <p class="leading-relaxed text-muted-foreground">
            Share with a named account by re-sealing the file key for them. Before anything is sent you see
            their key fingerprint; no public link exists to leak, and access can be revoked.
          </p>
          <p class="mt-auto rounded-lg bg-secondary px-4 py-3 font-mono text-xs tracking-[0.06em]">
            3C06 B3AC DFEA A038 CDFB 3784 CC7D A99B
          </p>
        </article>
        <article class="flex flex-col gap-5 rounded-xl border border-border bg-card p-7">
          <span class="font-mono text-xs text-muted-foreground">03 — Verify</span>
          <h3 class="text-2xl font-semibold">Changed means refused</h3>
          <p class="leading-relaxed text-muted-foreground">
            Every download is checked against its recorded SHA-256 and the audit chain, then by the cipher
            itself in your browser. A daily scan checks every stored file.
          </p>
          <p class="mt-auto flex flex-wrap gap-2.5 font-mono text-xs">
            <span class="rounded-lg bg-success-soft px-3 py-2 text-success">● Verified</span>
            <span class="rounded-lg bg-destructive-soft px-3 py-2 text-destructive">● Modified · refused</span>
          </p>
        </article>
      </div>
      <ul class="mt-10 flex flex-wrap gap-x-6 gap-y-2 border-t border-border pt-6 text-sm text-muted-foreground">
        <li v-for="item in alsoIncluded" :key="item">{{ item }}</li>
      </ul>
    </div>
  </section>
</template>
