<script setup lang="ts">
import { AlertCircle, CheckCircle, Download, Activity, Loader2, Share2, Shield, Trash2, X } from 'lucide-vue-next'
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { shareApi } from '@/api/share_api'
import type { SharedUser } from '@/api/share_api'
import { unwrapData } from '@/api/types'
import { exactBytes } from '@/utils/ciphertext-preview'

/**
 * Everything the list knows about one file, in one place: what it is, whether it is intact, who can
 * open it, and the actions. It adds no data of its own: the facts come from the list row, the
 * people from `GET /files/{id}/shared-users`, and every button hands the work back to the page's
 * own handler, so a download, share or delete behaves exactly as it does from the row.
 */
interface DetailFile {
  id: string
  name: string
  originalSize: string
  encryptedSize: string
  originalBytes: number
  encryptedBytes: number
  encryptedAt: string
  status: 'verified' | 'modified' | 'pending'
  owned: boolean
  ownerName: string
  algorithm: string
  mimeType: string | null
}

const props = defineProps<{ file: DetailFile; downloadBusy: boolean; downloading: boolean }>()
const emit = defineEmits<{
  (e: 'close'): void
  (e: 'download'): void
  (e: 'share'): void
  (e: 'check'): void
  (e: 'history'): void
  (e: 'delete'): void
}>()

const statusView = {
  verified: { label: 'Verified', icon: CheckCircle, className: 'bg-success-soft text-success' },
  modified: { label: 'Modified', icon: AlertCircle, className: 'bg-destructive-soft text-destructive' },
  pending: { label: 'Pending', icon: Shield, className: 'bg-muted text-muted-foreground' },
} as const

const people = ref<SharedUser[]>([])
const peopleState = ref<'idle' | 'loading' | 'error'>('idle')
const closeButton = ref<HTMLButtonElement | null>(null)

async function loadPeople() {
  people.value = []
  if (!props.file.owned) return
  peopleState.value = 'loading'
  try {
    people.value = unwrapData(await shareApi.sharedUsers(props.file.id)).users ?? []
    peopleState.value = 'idle'
  } catch {
    peopleState.value = 'error'
  }
}

function onKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape') emit('close')
}

onMounted(async () => {
  document.addEventListener('keydown', onKeydown)
  await nextTick()
  closeButton.value?.focus()
})
onBeforeUnmount(() => document.removeEventListener('keydown', onKeydown))
watch(() => props.file.id, loadPeople, { immediate: true })
</script>

<template>
  <div class="fixed inset-0 z-50" data-testid="file-detail">
    <div class="absolute inset-0 bg-black/30" @click="emit('close')" />
    <aside
      class="absolute inset-y-0 right-0 flex w-full max-w-md flex-col gap-6 overflow-y-auto border-l border-border bg-card p-6 shadow-xl"
      role="dialog"
      aria-modal="true"
      :aria-label="`Details of ${file.name}`"
    >
      <div class="flex items-start justify-between gap-4">
        <div class="flex min-w-0 flex-col gap-2">
          <p class="font-mono text-[0.68rem] uppercase tracking-[0.14em] text-muted-foreground">File</p>
          <h2 translate="no" class="text-xl font-semibold [overflow-wrap:anywhere]">{{ file.name }}</h2>
          <span class="inline-flex w-fit items-center gap-1.5 rounded-md px-2.5 py-1 font-mono text-xs" :class="statusView[file.status].className">
            <component :is="statusView[file.status].icon" class="h-3 w-3" aria-hidden="true" />
            {{ statusView[file.status].label }}
          </span>
        </div>
        <button
          ref="closeButton"
          type="button"
          class="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-md hover:bg-secondary"
          aria-label="Close details"
          @click="emit('close')"
        >
          <X class="h-4 w-4" />
        </button>
      </div>

      <dl class="grid grid-cols-[minmax(0,1fr)_minmax(0,1.5fr)] gap-x-4 gap-y-3 text-sm">
        <dt class="text-muted-foreground">Cipher</dt>
        <dd translate="no" class="font-mono text-[0.8rem]">{{ file.algorithm }}</dd>
        <dt class="text-muted-foreground">Original size</dt>
        <dd>{{ file.originalSize }} <span class="font-mono text-xs text-muted-foreground">{{ exactBytes(file.originalBytes) }}</span></dd>
        <dt class="text-muted-foreground">Stored size</dt>
        <dd>{{ file.encryptedSize }} <span class="font-mono text-xs text-muted-foreground">{{ exactBytes(file.encryptedBytes) }}</span></dd>
        <dt v-if="file.mimeType" class="text-muted-foreground">Type</dt>
        <dd v-if="file.mimeType" translate="no" class="font-mono text-[0.8rem]">{{ file.mimeType }}</dd>
        <dt class="text-muted-foreground">Uploaded</dt>
        <dd>{{ file.encryptedAt }}</dd>
        <dt class="text-muted-foreground">Owner</dt>
        <dd translate="no">{{ file.owned ? 'You' : file.ownerName }}</dd>
      </dl>

      <section class="flex flex-col gap-3 border-t border-border pt-5">
        <h3 class="text-sm font-semibold">Who can open it</h3>
        <p v-if="!file.owned" class="text-sm leading-relaxed text-muted-foreground">
          Shared with you by {{ file.ownerName }}. You open it with your own key, and the server never sees the file.
        </p>
        <template v-else>
          <p v-if="peopleState === 'loading'" class="flex items-center gap-2 text-sm text-muted-foreground"><Loader2 class="h-4 w-4 animate-spin" /> Loading…</p>
          <p v-else-if="peopleState === 'error'" class="text-sm text-destructive">The list of people could not be loaded.</p>
          <ul v-else class="flex flex-col divide-y divide-border rounded-lg border border-border text-sm">
            <li v-for="person in people" :key="person.user_id" class="flex items-center justify-between gap-3 px-3.5 py-2.5">
              <span translate="no" class="truncate">{{ person.is_owner ? 'You' : person.username }}</span>
              <span class="shrink-0 font-mono text-xs text-muted-foreground">
                {{ person.is_owner ? 'owner' : person.can_download ? 'can open' : 'view only' }}
              </span>
            </li>
            <li v-if="people.length <= 1" class="px-3.5 py-2.5 text-muted-foreground">Nobody else yet. Only you can open it.</li>
          </ul>
          <p class="text-xs leading-relaxed text-muted-foreground">The file key is also sealed for the recovery key.</p>
        </template>
      </section>

      <div class="mt-auto flex flex-col gap-2.5 border-t border-border pt-5">
        <button
          type="button"
          class="inline-flex h-11 items-center justify-center gap-2 rounded-lg bg-primary px-4 font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
          :disabled="downloadBusy"
          @click="emit('download')"
        >
          <Loader2 v-if="downloading" class="h-4 w-4 animate-spin" />
          <Download v-else class="h-4 w-4" />
          Download and decrypt
        </button>
        <div class="grid grid-cols-2 gap-2.5">
          <button v-if="file.owned" type="button" class="inline-flex h-10 items-center justify-center gap-2 rounded-lg border border-border px-3 text-sm hover:bg-secondary" @click="emit('share')">
            <Share2 class="h-4 w-4" /> Share
          </button>
          <button type="button" class="inline-flex h-10 items-center justify-center gap-2 rounded-lg border border-border px-3 text-sm hover:bg-secondary" @click="emit('check')">
            <Shield class="h-4 w-4" /> Check integrity
          </button>
          <button type="button" class="inline-flex h-10 items-center justify-center gap-2 rounded-lg border border-border px-3 text-sm hover:bg-secondary" @click="emit('history')">
            <Activity class="h-4 w-4" /> Access history
          </button>
          <button v-if="file.owned" type="button" class="inline-flex h-10 items-center justify-center gap-2 rounded-lg border border-border px-3 text-sm text-destructive hover:bg-destructive-soft" @click="emit('delete')">
            <Trash2 class="h-4 w-4" /> Delete
          </button>
        </div>
      </div>
    </aside>
  </div>
</template>
