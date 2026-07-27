<script setup lang="ts">
import { Code, LockKeyhole, Palette, Server } from 'lucide-vue-next'

const members = [
  {
    name: 'Wen Shuoxun',
    role: 'Testing Engineer',
    icon: Palette,
    bio: 'Designs user-first security workflows and plans product strategy.',
  },
  {
    name: 'Chen Tai',
    role: 'Encryption Engineer',
    icon: LockKeyhole,
    bio: 'Builds encryption modules and ensures secure key management.',
  },
  {
    name: 'Li Junyan',
    role: 'Frontend Developer',
    icon: Code,
    bio: 'Develops responsive interfaces and interaction experiences.',
  },
  {
    name: 'Jason Huang',
    role: 'Backend Engineer',
    icon: Server,
    bio: 'Maintains APIs, file pipelines, and system reliability.',
  },
]
</script>

<template>
  <section class="py-20">
    <div class="container mx-auto px-4">
      <div class="text-center mb-12">
        <h2 class="text-3xl md:text-4xl font-bold text-foreground mb-4">Development Team</h2>
        <p class="text-muted-foreground max-w-2xl mx-auto text-pretty">
          We are a cross-functional team focused on making encrypted file collaboration simple, safe, and reliable.
        </p>
      </div>

      <div class="max-w-6xl mx-auto grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
        <article v-for="member in members" :key="member.name" class="rounded-xl border border-border bg-card p-6">
          <div class="p-2 rounded-md bg-primary/10 w-fit mb-4">
            <component :is="member.icon" class="h-5 w-5 text-primary" />
          </div>
          <h3 class="text-lg font-semibold text-foreground">{{ member.name }}</h3>
          <p class="text-sm text-primary mt-1">{{ member.role }}</p>
          <p class="text-sm text-muted-foreground mt-3">{{ member.bio }}</p>
        </article>
      </div>
    </div>
  </section>
</template>
