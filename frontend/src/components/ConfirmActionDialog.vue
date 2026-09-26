<script setup lang="ts">
import { nextTick, onMounted, ref } from 'vue'
import { TriangleAlert } from 'lucide-vue-next'

withDefaults(
  defineProps<{
    title: string
    /** What will happen, and whether it can be undone. */
    consequence: string
    /** Optional extra context (filename, recipient, …). */
    detail?: string
    confirmLabel?: string
    busyLabel?: string
    busy?: boolean
  }>(),
  {
    confirmLabel: 'Confirm',
    busyLabel: 'Working…',
    busy: false,
  },
)

const emit = defineEmits<{
  (e: 'confirm'): void
  (e: 'close'): void
}>()

const confirmButton = ref<HTMLButtonElement | null>(null)

onMounted(async () => {
  await nextTick()
  // Focus Cancel's sibling confirm would be unsafe; land on the dialog chrome via confirm
  // only after the user has read — Cancel is first in tab order among actions, so the
  // confirm button is last. Focus the confirm so Enter is deliberate after reading.
  confirmButton.value?.focus()
})
</script>

<template>
  <div
    class="fixed inset-0 z-[60] flex items-center justify-center bg-black/40 p-4"
    @click.self="emit('close')"
  >
    <div
      role="dialog"
      aria-modal="true"
      :aria-labelledby="'confirm-action-title'"
      class="w-full max-w-md rounded-xl border border-destructive/40 bg-card p-6 shadow-xl"
    >
      <div class="mb-2 flex items-center gap-2">
        <div class="rounded-lg bg-destructive/10 p-2">
          <TriangleAlert class="h-4 w-4 text-destructive" />
        </div>
        <h2 id="confirm-action-title" class="text-lg font-semibold text-foreground">
          {{ title }}
        </h2>
      </div>

      <p v-if="detail" class="mb-2 text-sm font-medium text-foreground">{{ detail }}</p>
      <p class="text-sm text-muted-foreground">{{ consequence }}</p>

      <div class="mt-5 flex gap-2">
        <button
          type="button"
          class="h-10 flex-1 rounded-md border border-border px-4 text-sm text-foreground hover:bg-secondary disabled:opacity-50"
          :disabled="busy"
          @click="emit('close')"
        >
          Cancel
        </button>
        <button
          ref="confirmButton"
          type="button"
          class="h-10 flex-1 rounded-md bg-destructive px-4 text-sm text-white hover:bg-destructive/90 disabled:opacity-50"
          :disabled="busy"
          @click="emit('confirm')"
        >
          {{ busy ? busyLabel : confirmLabel }}
        </button>
      </div>
    </div>
  </div>
</template>
