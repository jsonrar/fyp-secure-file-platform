<script setup lang="ts">
import { BookOpen, MessageSquare, ShieldCheck, Users } from 'lucide-vue-next'
import { RouterLink } from 'vue-router'

const posts = [
  {
    title: 'How to encrypt a file in 30 seconds',
    author: 'Moderator',
    summary: 'A quick start walkthrough for uploading files, generating keys, and downloading encrypted outputs.',
  },
  {
    title: 'Best practices for sharing encrypted files',
    author: 'Security Team',
    summary: 'Set link expiration and access limits to reduce leakage risks in collaborative workflows.',
  },
  {
    title: 'Troubleshooting decryption failures',
    author: 'Education Mentor',
    summary: 'Common causes and practical fixes when keys, formats, or permissions do not match.',
  },
]

const guides = [
  {
    icon: ShieldCheck,
    title: 'Step 1: Upload your files',
    description: 'Drag and drop one or multiple files in the Product page.',
  },
  {
    icon: BookOpen,
    title: 'Step 2: Create a secure key',
    description: 'Use auto-generated keys or your own strong password.',
  },
  {
    icon: MessageSquare,
    title: 'Step 3: Encrypt and verify',
    description: 'Run encryption, then review file status and access records.',
  },
]
</script>

<template>
  <section class="py-20">
    <div class="container mx-auto px-4">
      <div class="text-center mb-12">
        <h2 class="text-3xl md:text-4xl font-bold text-foreground mb-4">Education</h2>
        <p class="text-muted-foreground max-w-2xl mx-auto text-pretty">
          Learn how to use SecureView effectively, discover practical tips, and follow secure file sharing workflows.
        </p>
      </div>

      <div class="max-w-6xl mx-auto grid lg:grid-cols-3 gap-6 mb-8">
        <article v-for="post in posts" :key="post.title" class="rounded-xl border border-border bg-card p-6">
          <p class="text-xs text-primary font-medium mb-2">{{ post.author }}</p>
          <h3 class="text-lg font-semibold text-foreground mb-3">{{ post.title }}</h3>
          <p class="text-sm text-muted-foreground">{{ post.summary }}</p>
        </article>
      </div>

      <div class="max-w-4xl mx-auto rounded-xl border border-border bg-card p-6 md:p-8">
        <div class="flex items-center justify-between gap-4 flex-wrap mb-6">
          <div class="flex items-center gap-2">
            <Users class="h-5 w-5 text-primary" />
            <h3 class="text-xl font-semibold text-foreground">Quick Guide</h3>
          </div>
          <RouterLink to="/upload" class="h-10 px-4 inline-flex items-center rounded-md bg-primary text-primary-foreground hover:bg-primary/90 transition-colors">
            Use Product
          </RouterLink>
        </div>
        <div class="space-y-4">
          <div v-for="guide in guides" :key="guide.title" class="rounded-lg border border-border bg-secondary/30 p-4">
            <div class="flex items-start gap-3">
              <div class="p-2 rounded-md bg-primary/10">
                <component :is="guide.icon" class="h-4 w-4 text-primary" />
              </div>
              <div>
                <h4 class="text-foreground font-medium">{{ guide.title }}</h4>
                <p class="text-sm text-muted-foreground mt-1">{{ guide.description }}</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
