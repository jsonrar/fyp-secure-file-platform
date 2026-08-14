<script setup lang="ts">
import { computed, ref } from 'vue'
import { ArrowRight, CheckCircle2, Info, Shield } from 'lucide-vue-next'
import { algorithms, type AlgorithmId } from '@/data/education/algorithms'

const selectedId = ref<AlgorithmId>('aes')
const selected = computed(() => algorithms.find((a) => a.id === selectedId.value)!)

const typeBadge: Record<string, string> = {
  symmetric: 'Symmetric',
  asymmetric: 'Asymmetric',
  hash: 'Hash Function',
  kdf: 'Key Derivation',
}
</script>

<template>
  <div class="grid lg:grid-cols-[240px_1fr] gap-6">
    <aside class="space-y-2">
      <p class="text-xs font-medium text-muted-foreground uppercase tracking-wide px-1 mb-3">Select Algorithm</p>
      <button
        v-for="algo in algorithms"
        :key="algo.id"
        type="button"
        class="w-full text-left rounded-lg border px-4 py-3 transition-colors"
        :class="
          selectedId === algo.id
            ? 'border-primary bg-primary/10 text-foreground'
            : 'border-border bg-card text-muted-foreground hover:border-primary/40 hover:text-foreground'
        "
        @click="selectedId = algo.id"
      >
        <span class="font-semibold block">{{ algo.shortLabel }}</span>
        <span class="text-xs mt-0.5 block opacity-80">{{ typeBadge[algo.type] }}</span>
      </button>
    </aside>

    <article class="rounded-xl border border-border bg-card p-6 md:p-8">
      <div class="flex flex-wrap items-start justify-between gap-4 mb-6">
        <div>
          <span class="inline-flex items-center gap-1.5 text-xs font-medium text-primary bg-primary/10 px-2.5 py-1 rounded-full mb-3">
            <Shield class="h-3.5 w-3.5" />
            {{ typeBadge[selected.type] }}
          </span>
          <h3 class="text-2xl font-bold text-foreground">{{ selected.name }}</h3>
          <p class="text-muted-foreground mt-2 max-w-2xl">{{ selected.tagline }}</p>
        </div>
      </div>

      <p class="text-sm text-foreground leading-relaxed mb-8">{{ selected.summary }}</p>

      <div class="mb-8">
        <h4 class="text-sm font-semibold text-foreground mb-4 flex items-center gap-2">
          <ArrowRight class="h-4 w-4 text-primary" />
          How It Works
        </h4>
        <div class="space-y-3">
          <div
            v-for="(step, i) in selected.howItWorks"
            :key="step.title"
            class="flex gap-4 rounded-lg border border-border bg-secondary/20 p-4"
          >
            <div class="flex-shrink-0 h-8 w-8 rounded-full bg-primary/15 text-primary text-sm font-bold flex items-center justify-center">
              {{ i + 1 }}
            </div>
            <div>
              <p class="font-medium text-foreground">{{ step.title.replace(/^\d+\.\s*/, '') }}</p>
              <p class="text-sm text-muted-foreground mt-1">{{ step.description }}</p>
            </div>
          </div>
        </div>
      </div>

      <div class="grid md:grid-cols-3 gap-4 mb-8">
        <div class="rounded-lg border border-border p-4">
          <p class="text-xs font-medium text-primary mb-2">Use Cases</p>
          <ul class="space-y-1.5">
            <li v-for="item in selected.useCases" :key="item" class="text-sm text-muted-foreground flex gap-2">
              <CheckCircle2 class="h-4 w-4 text-primary flex-shrink-0 mt-0.5" />
              {{ item }}
            </li>
          </ul>
        </div>
        <div class="rounded-lg border border-border p-4">
          <p class="text-xs font-medium text-primary mb-2">Strengths</p>
          <ul class="space-y-1.5">
            <li v-for="item in selected.strengths" :key="item" class="text-sm text-muted-foreground">• {{ item }}</li>
          </ul>
        </div>
        <div class="rounded-lg border border-border p-4">
          <p class="text-xs font-medium text-destructive mb-2">Limitations</p>
          <ul class="space-y-1.5">
            <li v-for="item in selected.limitations" :key="item" class="text-sm text-muted-foreground">• {{ item }}</li>
          </ul>
        </div>
      </div>

      <div class="rounded-lg border border-primary/20 bg-primary/5 p-4">
        <p class="text-xs font-medium text-primary mb-2 flex items-center gap-1.5">
          <Info class="h-3.5 w-3.5" />
          Key Facts
        </p>
        <ul class="space-y-1">
          <li v-for="fact in selected.keyFacts" :key="fact" class="text-sm text-foreground">• {{ fact }}</li>
        </ul>
      </div>
    </article>
  </div>
</template>
