<script setup lang="ts">
import { ref } from 'vue'
import { shareApi } from '@/api/share_api'

const props = defineProps<{
  fileId: string
}>()

const emit = defineEmits<{
  (e: 'close'): void
}>()

const targetUsername = ref('')
const message = ref('')
const isSubmitting = ref(false)

async function share() {
  if (!targetUsername.value.trim()) return
  isSubmitting.value = true
  message.value = ''
  try {
    await shareApi.shareFile(props.fileId, { target_username: targetUsername.value.trim() })
    message.value = 'Share request sent'
  } catch (error) {
    message.value = error instanceof Error ? error.message : 'Share failed'
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" @click.self="emit('close')">
    <div class="w-full max-w-md rounded-xl border border-border bg-card p-6 shadow-xl">
      <h2 class="text-lg font-semibold text-foreground mb-2">Share File #{{ fileId }}</h2>
      <p class="text-sm text-muted-foreground mb-4">Enter the username to grant access via the backend sharing API.</p>
      <input
        v-model="targetUsername"
        placeholder="Target username"
        class="h-10 w-full rounded-md border border-border bg-secondary px-3 text-foreground"
      />
      <div class="mt-4 flex gap-2">
        <button
          class="flex-1 h-10 rounded-md bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
          :disabled="isSubmitting || !targetUsername.trim()"
          @click="share"
        >
          Share
        </button>
        <button class="h-10 px-4 rounded-md border border-border hover:bg-secondary" @click="emit('close')">
          Close
        </button>
      </div>
      <p v-if="message" class="text-sm text-muted-foreground mt-3">{{ message }}</p>
    </div>
  </div>
</template>
