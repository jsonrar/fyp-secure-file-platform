<script setup lang="ts">
import FileEncryption from '@/components/securfile/file-encryption.vue'
import SecurityStory from '@/components/explainers/SecurityStory.vue'
</script>

<template>
  <FileEncryption />
  <!-- Explain the file lifecycle below the upload controls. -->
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


</template>
