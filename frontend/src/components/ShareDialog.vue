<script setup lang="ts">
import { nextTick, onMounted, ref } from 'vue'
import { Share2 } from 'lucide-vue-next'

import {
  FileKeyUnwrapError,
  KeyNotUnlockedError,
  NotUnlockedError,
} from '@/crypto/download'
import { RecipientNotFoundError, shareFileWithUsername } from '@/crypto/share'
import { apiErrorMessage } from '@/api/http'

const props = defineProps<{
  fileId: string
  filename?: string
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'shared', username: string): void
  /** The account key must be opened before the file's key can be rewrapped. */
  (e: 'needs-unlock', keyId: string | null): void
}>()

const targetUsername = ref('')
const errorMessage = ref('')
const isSubmitting = ref(false)
const field = ref<HTMLInputElement | null>(null)

onMounted(async () => {
  await nextTick()
  field.value?.focus()
})

async function share() {
  const name = targetUsername.value.trim()
  if (!name) {
    errorMessage.value = 'Enter the username to share with'
    return
  }
  isSubmitting.value = true
  errorMessage.value = ''
  try {
    await shareFileWithUsername(props.fileId, name)
    emit('shared', name)
  } catch (error) {
    // Unlocking is not a failure: the caller raises the passphrase dialog and the user
    // comes back to this one.
    if (error instanceof NotUnlockedError) {
      emit('needs-unlock', null)
      return
    }
    if (error instanceof KeyNotUnlockedError) {
      emit('needs-unlock', error.keyId)
      return
    }
    errorMessage.value =
      error instanceof RecipientNotFoundError
        ? `No account named "${name}". Check the spelling with them — usernames must match exactly.`
        : error instanceof FileKeyUnwrapError
          ? 'Your account key does not open this file, so it cannot be shared from here.'
          : apiErrorMessage(error, 'Could not share this file')
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <div
    class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
    @click.self="emit('close')"
  >
    <div class="w-full max-w-md rounded-xl border border-border bg-card p-6 shadow-xl">
      <div class="flex items-center gap-2 mb-2">
        <div class="p-2 rounded-lg bg-secondary"><Share2 class="h-4 w-4 text-primary" /></div>
        <h2 class="text-lg font-semibold text-foreground">Share this file</h2>
      </div>

      <p class="text-sm text-muted-foreground mb-4">
        <span v-if="props.filename" class="text-foreground">{{ props.filename }}</span>
        <span v-else>This file</span>
        is re-encrypted to the recipient's own key in this browser. They open it with their
        own passphrase — never yours — and the server never sees the file's key.
      </p>

      <form @submit.prevent="share">
        <label class="text-sm text-foreground mb-2 block">
          Recipient's username <span class="text-destructive">*</span>
        </label>
        <input
          ref="field"
          v-model="targetUsername"
          placeholder="Their username on SecureView"
          autocomplete="off"
          class="h-10 w-full rounded-md border border-border bg-secondary px-3 text-foreground"
        />
        <p class="text-xs text-muted-foreground mt-2">
          They need a SecureView account. Sharing is per account, not by link — a file can
          only be re-encrypted to a key that already exists.
        </p>

        <p v-if="errorMessage" class="text-sm text-destructive mt-2">{{ errorMessage }}</p>

        <div class="mt-4 flex gap-2">
          <button
            type="submit"
            class="flex-1 h-10 rounded-md bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            :disabled="isSubmitting || !targetUsername.trim()"
          >
            {{ isSubmitting ? 'Sharing...' : 'Share' }}
          </button>
          <button
            type="button"
            class="h-10 px-4 rounded-md border border-border hover:bg-secondary"
            @click="emit('close')"
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
  </div>
</template>
