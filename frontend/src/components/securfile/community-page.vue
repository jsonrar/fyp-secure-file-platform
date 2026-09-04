<script setup lang="ts">
import { ref } from 'vue'
import { BookOpen, Clapperboard, FlaskConical, GraduationCap, Layers } from 'lucide-vue-next'
import AlgorithmExplorer from '@/components/education/AlgorithmExplorer.vue'
import CryptoPlayground from '@/components/education/CryptoPlayground.vue'
import KnowledgeSearch from '@/components/education/KnowledgeSearch.vue'
import SoftwareGuide from '@/components/education/SoftwareGuide.vue'

type SectionId = 'algorithms' | 'software' | 'playground' | 'knowledge'

const activeSection = ref<SectionId>('algorithms')

const sections: { id: SectionId; label: string; description: string; icon: typeof Layers }[] = [
  {
    id: 'algorithms',
    label: 'Algorithm Explorer',
    description: 'Learn AES-128, AES-256, RSA, SHA, ChaCha20, and Argon2id with animated demos.',
    icon: Layers,
  },
  {
    id: 'playground',
    label: 'Playground',
    description: 'Try Caesar, Vigenère, Rail Fence, AES, and RSA interactively in your browser.',
    icon: FlaskConical,
  },
  {
    id: 'knowledge',
    label: 'Knowledge Base',
    description: 'Search articles on encryption basics, keys, and best practices.',
    icon: BookOpen,
  },
  {
    id: 'software',
    label: 'How to Use',
    description: 'Video walkthroughs that show how to encrypt, upload, and share in SecureView.',
    icon: Clapperboard,
  },
]
</script>

<template>
  <section class="py-16 md:py-24">
    <div class="container mx-auto px-4">
      <div class="text-center mb-12 max-w-3xl mx-auto">
        <div class="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary/10 border border-primary/20 mb-5">
          <GraduationCap class="h-4 w-4 text-primary" />
          <span class="text-sm text-primary font-medium">Encryption Education</span>
        </div>
        <h1 class="text-3xl md:text-5xl font-bold text-foreground mb-4 text-balance">Learn How Encryption Works</h1>
        <p class="text-muted-foreground text-lg text-pretty">
          Explore algorithms, watch how SecureView is used, try hands-on demos, and search the knowledge library.
        </p>
      </div>

      <div class="max-w-6xl mx-auto mb-10">
        <div class="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
          <button
            v-for="section in sections"
            :key="section.id"
            type="button"
            class="rounded-xl border p-4 text-left transition-all"
            :class="
              activeSection === section.id
                ? 'border-primary bg-primary/10 shadow-sm'
                : 'border-border bg-card hover:border-primary/30'
            "
            @click="activeSection = section.id"
          >
            <component
              :is="section.icon"
              class="h-5 w-5 mb-2"
              :class="activeSection === section.id ? 'text-primary' : 'text-muted-foreground'"
            />
            <p class="font-semibold text-foreground">{{ section.label }}</p>
            <p class="text-xs text-muted-foreground mt-1 leading-relaxed">{{ section.description }}</p>
          </button>
        </div>
      </div>

      <div class="max-w-6xl mx-auto">
        <AlgorithmExplorer v-if="activeSection === 'algorithms'" />
        <SoftwareGuide v-else-if="activeSection === 'software'" />
        <CryptoPlayground v-else-if="activeSection === 'playground'" />
        <KnowledgeSearch v-else-if="activeSection === 'knowledge'" />
      </div>
    </div>
  </section>
</template>
