<script setup lang="ts">
import { Check, Circle, KeyRound, Lock, RefreshCw, UploadCloud, FileText } from 'lucide-vue-next'
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { formatFileSize } from '@/api/types'
import type { UploadStage } from '@/crypto/upload'

const props = defineProps<{
  fileName: string
  fileSize: number
  algorithm: string
  /** The stage now running; null once the file is done. */
  stage: UploadStage | null
  durations: Partial<Record<UploadStage, number>>
  uploadFraction: number
  plaintextHead: Uint8Array | null
  ciphertextHead: Uint8Array | null
  done: boolean
}>()

const ORDER: UploadStage[] = ['read', 'encrypt', 'wrap', 'upload']

const steps = computed(() => [
  { stage: 'read' as const, icon: FileText, title: 'Read the file in this browser', detail: formatFileSize(props.fileSize) },
  {
    stage: 'encrypt' as const,
    icon: Lock,
    title: `Encrypt with ${props.algorithm}`,
    detail: 'Fresh random key and nonce, then decrypted once to check it',
  },
  {
    stage: 'wrap' as const,
    icon: KeyRound,
    title: 'Lock the file key with RSA-OAEP',
    detail: 'One copy for your public key, one for the recovery key',
  },
  { stage: 'upload' as const, icon: UploadCloud, title: 'Upload the ciphertext only', detail: 'The server never sees the readable file' },
])

function stateOf(stage: UploadStage): 'done' | 'active' | 'waiting' {
  if (props.done || props.durations[stage] !== undefined) return 'done'
  if (props.stage === stage) return 'active'
  return ORDER.indexOf(stage) < ORDER.indexOf(props.stage ?? 'read') ? 'done' : 'waiting'
}

function formatMs(ms: number | undefined): string {
  if (ms === undefined) return ''
  return ms < 1000 ? `${Math.max(1, Math.round(ms))} ms` : `${(ms / 1000).toFixed(1)} s`
}

const toHex = (bytes: Uint8Array) => Array.from(bytes, (b) => b.toString(16).padStart(2, '0'))
const toText = (bytes: Uint8Array) =>
  Array.from(bytes, (b) => (b >= 0x20 && b < 0x7f ? String.fromCharCode(b) : '·')).join('')

const plainHex = computed(() => (props.plaintextHead ? toHex(props.plaintextHead) : []))
const cipherHex = computed(() => (props.ciphertextHead ? toHex(props.ciphertextHead) : []))

/** Bytes still shown as scrambling; each settles on its real value in turn. */
const shownCipher = ref<string[]>([])
let timer: ReturnType<typeof setInterval> | undefined

const reduceMotion =
  typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches

watch(
  cipherHex,
  (real) => {
    clearInterval(timer)
    if (!real.length || reduceMotion) {
      shownCipher.value = real
      return
    }
    let settled = 0
    timer = setInterval(() => {
      settled += 1
      shownCipher.value = real.map((byte, i) =>
        i < settled ? byte : Math.floor(Math.random() * 256).toString(16).padStart(2, '0'),
      )
      if (settled >= real.length) clearInterval(timer)
    }, 35)
  },
  { immediate: true },
)

onBeforeUnmount(() => clearInterval(timer))
</script>

<template>
  <div class="rounded-lg border border-border bg-secondary/30 p-4" data-testid="encryption-progress" aria-live="polite">
    <p class="mb-3 text-sm font-medium text-foreground">
      <span translate="no" class="[overflow-wrap:anywhere]">{{ fileName }}</span>
    </p>

    <ol class="space-y-3">
      <li v-for="step in steps" :key="step.stage" class="flex items-start gap-3">
        <span
          class="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full border transition-colors"
          :class="{
            'border-primary bg-primary text-primary-foreground': stateOf(step.stage) === 'done',
            'border-primary text-primary': stateOf(step.stage) === 'active',
            'border-border text-muted-foreground': stateOf(step.stage) === 'waiting',
          }"
        >
          <Check v-if="stateOf(step.stage) === 'done'" class="h-3.5 w-3.5" />
          <RefreshCw v-else-if="stateOf(step.stage) === 'active'" class="h-3.5 w-3.5 animate-spin" />
          <Circle v-else class="h-2 w-2" />
        </span>
        <div class="min-w-0 flex-1">
          <div class="flex items-baseline justify-between gap-2">
            <p
              class="flex items-center gap-1.5 text-sm"
              :class="stateOf(step.stage) === 'waiting' ? 'text-muted-foreground' : 'text-foreground'"
            >
              <component :is="step.icon" class="h-3.5 w-3.5 shrink-0" />
              <span>{{ step.title }}</span>
            </p>
            <span v-if="durations[step.stage] !== undefined" class="shrink-0 font-mono text-xs text-muted-foreground">
              {{ formatMs(durations[step.stage]) }}
            </span>
          </div>
          <p class="text-xs text-muted-foreground">{{ step.detail }}</p>
          <div
            v-if="step.stage === 'upload' && stateOf('upload') === 'active'"
            class="mt-2 h-1.5 overflow-hidden rounded-full bg-border"
          >
            <div class="h-full bg-primary transition-[width] duration-200" :style="{ width: `${Math.round(uploadFraction * 100)}%` }" />
          </div>
        </div>
      </li>
    </ol>

    <div v-if="plaintextHead && ciphertextHead" class="mt-4 space-y-2 border-t border-border pt-3" data-testid="byte-comparison">
      <p class="text-xs text-muted-foreground">The first {{ plainHex.length }} bytes, before and after encryption:</p>
      <div>
        <p class="text-xs text-muted-foreground">Your file</p>
        <p translate="no" class="break-all font-mono text-xs text-foreground">{{ plainHex.join(' ') }}</p>
        <p translate="no" class="font-mono text-xs text-muted-foreground">{{ toText(plaintextHead) }}</p>
      </div>
      <div>
        <p class="flex items-center gap-1 text-xs text-primary"><Lock class="h-3 w-3" /> What the server receives</p>
        <p translate="no" class="break-all font-mono text-xs text-primary">{{ shownCipher.join(' ') }}</p>
      </div>
    </div>
  </div>
</template>
