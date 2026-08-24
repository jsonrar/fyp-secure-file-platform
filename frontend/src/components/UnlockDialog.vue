<script setup lang="ts">
import { nextTick, onMounted, ref } from 'vue'
import { KeyRound } from 'lucide-vue-next'

import PasswordField from '@/components/PasswordField.vue'
import { unlockOwnedKey, unlockWithPassphrase } from '@/crypto/download'
import { PassphraseRejectedError } from '@/utils/account-crypto'

const props = defineProps<{
  /** Set when a specific superseded key is needed, rather than the active one. */
  keyId?: string | null
}>()

const emit = defineEmits<{
  (e: 'unlocked'): void
  (e: 'close'): void
}>()

const passphrase = ref('')
const errorMessage = ref('')
const isUnlocking = ref(false)
const field = ref<InstanceType<typeof PasswordField> | null>(null)

onMounted(async () => {
  await nextTick()
  field.value?.focus()
})

async function unlock() {
  if (!passphrase.value) {
    errorMessage.value = 'Enter your encryption passphrase'
    return
  }
  isUnlocking.value = true
  errorMessage.value = ''
  try {
    if (props.keyId) {
      await unlockOwnedKey(props.keyId, passphrase.value)
    } else {
      await unlockWithPassphrase(passphrase.value)
    }
    // Drop the passphrase as soon as it has done its work. The unwrapped key lives on as
    // a non-extractable CryptoKey; keeping the string around buys nothing and loses if
    // anything later serialises this component's state.
    passphrase.value = ''
    emit('unlocked')
  } catch (error) {
    passphrase.value = ''
    errorMessage.value =
      error instanceof PassphraseRejectedError
        ? 'That passphrase does not open your account key.'
        : error instanceof Error
          ? error.message
          : 'Could not unlock the account key'
    await nextTick()
    field.value?.focus()
  } finally {
    isUnlocking.value = false
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
        <div class="p-2 rounded-lg bg-secondary"><KeyRound class="h-4 w-4 text-primary" /></div>
        <h2 class="text-lg font-semibold text-foreground">Unlock your files</h2>
      </div>
      <p class="text-sm text-muted-foreground mb-4">
        Your files are decrypted in this browser, so your encryption passphrase is needed to
        open the account key. It is never sent to the server.
      </p>
      <p v-if="props.keyId" class="text-sm text-muted-foreground mb-4">
        This file was encrypted under an earlier account key
        (<code class="text-xs">{{ props.keyId }}</code
        >), which the same passphrase opens.
      </p>

      <form @submit.prevent="unlock">
        <PasswordField
          ref="field"
          v-model="passphrase"
          label="Encryption passphrase"
          placeholder="Your encryption passphrase"
          autocomplete="current-password"
        />
        <p v-if="errorMessage" class="text-sm text-destructive mt-2">{{ errorMessage }}</p>

        <div class="mt-4 flex gap-2">
          <button
            type="submit"
            class="flex-1 h-10 rounded-md bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            :disabled="isUnlocking"
          >
            {{ isUnlocking ? 'Unlocking...' : 'Unlock' }}
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

      <p class="text-xs text-muted-foreground mt-4">
        Deriving the key takes a moment on purpose: the same cost that slows this down slows
        an attacker guessing the passphrase offline.
      </p>
    </div>
  </div>
</template>
