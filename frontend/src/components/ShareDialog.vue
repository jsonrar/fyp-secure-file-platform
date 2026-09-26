<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from 'vue'
import { Loader2, Share2, UserMinus } from 'lucide-vue-next'

import {
  FileKeyUnwrapError,
  KeyNotUnlockedError,
  NotUnlockedError,
} from '@/crypto/download'
import { RecipientNotFoundError, shareFileWithRecipient } from '@/crypto/share'
import { apiErrorMessage } from '@/api/http'
import { shareApi, type SharedUser } from '@/api/share_api'
import { unwrapData } from '@/api/types'
import ConfirmActionDialog from '@/components/ConfirmActionDialog.vue'

const props = defineProps<{
  fileId: string
  filename?: string
  initialRecipient?: string
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'shared', username: string): void
  (e: 'revoked', username: string): void
  /** The account key must be opened before the file's key can be rewrapped. */
  (e: 'needs-unlock', keyId: string | null, recipient: string): void
}>()

const targetUsername = ref(props.initialRecipient ?? '')
const errorMessage = ref('')
const isSubmitting = ref(false)
const field = ref<HTMLInputElement | null>(null)

const recipients = ref<SharedUser[]>([])
const isLoadingRecipients = ref(true)
const revokingUserId = ref<string | null>(null)
/** Recipient selected for revoke confirmation; null when the dialog is closed. */
const pendingRevoke = ref<SharedUser | null>(null)

/** The owner holds a canonical grant that cannot be revoked, so it is not offered. */
const others = computed(() => recipients.value.filter((user) => !user.is_owner))

/**
 * Who currently holds this file.
 *
 * `GET /files/{id}/shared-users` existed and nothing called it, so a share, once made, was
 * invisible and irreversible from the interface -- there was no list of who held the file
 * and no way to take it back.
 */
const loadRecipients = async () => {
  isLoadingRecipients.value = true
  try {
    recipients.value = unwrapData(await shareApi.sharedUsers(props.fileId)).users ?? []
  } catch {
    // Not fatal: sharing with someone new still works without the current list.
    recipients.value = []
  } finally {
    isLoadingRecipients.value = false
  }
}

function requestRevoke(user: SharedUser) {
  pendingRevoke.value = user
}

/**
 * Runs only after the confirmation dialog. Revoke used to fire on the first click of the
 * icon, which #72 requires to state the consequence first.
 */
async function confirmRevoke() {
  const user = pendingRevoke.value
  if (!user) return
  revokingUserId.value = user.user_id
  errorMessage.value = ''
  try {
    await shareApi.revokeAccess(props.fileId, { target_user_id: user.user_id })
    pendingRevoke.value = null
    await loadRecipients()
    emit('revoked', user.username)
  } catch (error) {
    errorMessage.value = apiErrorMessage(error, `Could not revoke ${user.username}'s access`)
  } finally {
    revokingUserId.value = null
  }
}

function closePendingRevoke() {
  if (revokingUserId.value !== null) return
  pendingRevoke.value = null
}

onMounted(async () => {
  loadRecipients()
  await nextTick()
  field.value?.focus()
})

async function share() {
  const name = targetUsername.value.trim()
  if (!name) {
    errorMessage.value = 'Enter the username or email address to share with'
    return
  }
  isSubmitting.value = true
  errorMessage.value = ''
  try {
    await shareFileWithRecipient(props.fileId, name)
    targetUsername.value = ''
    await loadRecipients()
    emit('shared', name)
  } catch (error) {
    // Unlocking is not a failure: the caller raises the passphrase dialog and the user
    // comes back to this one.
    if (error instanceof NotUnlockedError) {
      emit('needs-unlock', null, name)
      return
    }
    if (error instanceof KeyNotUnlockedError) {
      emit('needs-unlock', error.keyId, name)
      return
    }
    errorMessage.value =
      error instanceof RecipientNotFoundError
        ? `No account matches "${name}". Check their exact SecureView username or email address.`
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

      <div class="mb-5 pb-5 border-b border-border">
        <p class="text-sm text-foreground mb-2">Currently shared with</p>

        <div v-if="isLoadingRecipients" class="py-2 text-sm text-muted-foreground">
          <Loader2 class="h-4 w-4 animate-spin" />
        </div>

        <p v-else-if="!others.length" class="text-sm text-muted-foreground">
          Nobody yet — only you can open this file.
        </p>

        <ul v-else class="divide-y divide-border">
          <li
            v-for="user in others"
            :key="user.user_id"
            class="flex items-center justify-between gap-3 py-2"
          >
            <div class="min-w-0">
              <p class="text-sm text-foreground truncate">{{ user.username }}</p>
              <p class="text-xs text-muted-foreground">
                Since {{ new Date(user.granted_at).toLocaleDateString() }}
                <span v-if="!user.can_download"> · view only</span>
              </p>
            </div>
            <button
              type="button"
              class="h-8 px-2 inline-flex items-center gap-1 rounded-md border border-destructive/40 text-destructive text-xs hover:bg-destructive/10 disabled:opacity-50"
              :disabled="revokingUserId !== null"
              @click="requestRevoke(user)"
            >
              <Loader2 v-if="revokingUserId === user.user_id" class="h-3 w-3 animate-spin" />
              <UserMinus v-else class="h-3 w-3" />
              Revoke
            </button>
          </li>
        </ul>

        <p v-if="others.length" class="text-xs text-muted-foreground mt-3">
          Revoking stops further access and removes the file from their list. It cannot
          recover a copy they have already downloaded and decrypted.
        </p>
      </div>

      <form @submit.prevent="share">
        <label class="text-sm text-foreground mb-2 block">
          Share with someone else <span class="text-destructive">*</span>
        </label>
        <input
          ref="field"
          v-model="targetUsername"
          placeholder="Their username/ Email address on Secureview."
          autocomplete="off"
          class="h-10 w-full rounded-md border border-border bg-secondary px-3 text-foreground"
        />
        <p class="text-xs text-muted-foreground mt-2">
          They need a SecureView account. Sharing is per account, not by link — a file can
          only be re-encrypted to a key that already exists. Enter their exact username or
          email address.
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

  <ConfirmActionDialog
    v-if="pendingRevoke"
    title="Revoke access?"
    :detail="`Remove ${pendingRevoke.username}'s access${filename ? ` to ${filename}` : ''}?`"
    consequence="They lose further access and the file leaves their Shared with me list. A copy they have already downloaded and decrypted cannot be recovered."
    confirm-label="Revoke access"
    busy-label="Revoking…"
    :busy="revokingUserId === pendingRevoke.user_id"
    @confirm="confirmRevoke"
    @close="closePendingRevoke"
  />
</template>
