<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from 'vue'
import { CheckCircle, KeyRound, Loader2 } from 'lucide-vue-next'
import PasswordField from '@/components/PasswordField.vue'
import { apiErrorMessage } from '@/api/http'
import { PrivateKeyMismatchError } from '@/crypto/download'
import {
  PassphraseTooShortError,
  ResetVerificationError,
  resetPassphraseWithPrivateKeyPem,
} from '@/crypto/passphrase-reset'
import { PASSPHRASE_MIN_LENGTH } from '@/utils/password-policy'

/**
 * Set a new encryption passphrase using the private key file issued at registration.
 *
 * The file is read in the page and never uploaded: it is the plaintext account private key.
 * Only the two re-sealed envelopes and a signature over them reach the server.
 */

const keyPem = ref('')
const keyFileName = ref('')
const passphrase = ref('')
const confirmation = ref('')
const submitted = ref(false)
const busy = ref(false)
const errorMessage = ref('')
const done = ref(false)
const acknowledged = ref(false)

// Leaving the page must not leave the plaintext key file sitting in component state.
onBeforeUnmount(() => {
  keyPem.value = ''
  passphrase.value = ''
  confirmation.value = ''
})

const passphraseError = computed(() => {
  if (!submitted.value) return ''
  if (passphrase.value.length < PASSPHRASE_MIN_LENGTH) {
    return `Use at least ${PASSPHRASE_MIN_LENGTH} characters.`
  }
  return ''
})

const confirmationError = computed(() => {
  if (!submitted.value) return ''
  return confirmation.value === passphrase.value ? '' : 'The two passphrases do not match.'
})

async function chooseKeyFile(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  // Reset immediately so choosing the same file twice after a failure still fires a change.
  input.value = ''
  if (!file) return
  keyFileName.value = file.name
  keyPem.value = await file.text()
  errorMessage.value = ''
}

async function submit() {
  submitted.value = true
  errorMessage.value = ''
  if (!keyPem.value) {
    errorMessage.value = 'Choose the private key file you saved at registration.'
    return
  }
  if (passphraseError.value || confirmationError.value) return
  if (!acknowledged.value) {
    errorMessage.value = 'Confirm that you understand the old passphrase will stop working.'
    return
  }

  busy.value = true
  try {
    await resetPassphraseWithPrivateKeyPem(keyPem.value, passphrase.value)
    done.value = true
    // Nothing sensitive should outlive the form.
    keyPem.value = ''
    passphrase.value = ''
    confirmation.value = ''
    acknowledged.value = false
  } catch (error) {
    if (error instanceof PrivateKeyMismatchError) {
      errorMessage.value =
        'That key file does not belong to this account. Check you saved it from this account.'
    } else if (error instanceof TypeError) {
      errorMessage.value = error.message
    } else if (error instanceof PassphraseTooShortError || error instanceof ResetVerificationError) {
      errorMessage.value = error.message
    } else {
      errorMessage.value = apiErrorMessage(error, 'The passphrase could not be reset')
    }
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="mt-6 rounded-xl border border-border bg-card p-6">
    <h2 class="flex items-center gap-2 text-lg font-semibold text-foreground">
      <KeyRound class="h-5 w-5 text-primary" />
      Forgot your encryption passphrase?
    </h2>
    <p class="mt-2 max-w-2xl text-sm text-muted-foreground">
      Set a new one with the private key file you were given once at registration. Your files,
      your shares, and your account key stay exactly as they are; only the passphrase that
      unlocks the key changes. The file is read in this browser and is never uploaded.
    </p>

    <div v-if="done" class="mt-4 flex items-start gap-2 rounded-lg border border-primary/40 bg-primary/5 p-3">
      <CheckCircle class="mt-0.5 h-4 w-4 shrink-0 text-primary" />
      <p class="text-sm text-foreground">
        Your new passphrase is set and was checked against what the server now stores. Keep
        your private key file somewhere safe; it is still the only way back if you forget this
        passphrase too.
      </p>
    </div>

    <form v-else class="mt-4 space-y-4" novalidate @submit.prevent="submit">
      <div>
        <label class="inline-flex h-10 cursor-pointer items-center rounded-md border border-border px-4 text-sm text-foreground transition-colors hover:bg-secondary">
          <span>{{ keyFileName || 'Choose private key file' }}</span>
          <input
            type="file"
            accept=".pem,application/x-pem-file,text/plain"
            class="hidden"
            :disabled="busy"
            @change="chooseKeyFile"
          />
        </label>
      </div>

      <PasswordField
        v-model="passphrase"
        label="New encryption passphrase"
        :hint="`At least ${PASSPHRASE_MIN_LENGTH} characters. Not your login password.`"
        :error="passphraseError"
      />
      <PasswordField
        v-model="confirmation"
        label="Confirm new passphrase"
        :error="confirmationError"
      />

      <label class="flex items-start gap-2 text-sm text-foreground">
        <input v-model="acknowledged" type="checkbox" class="mt-1" :disabled="busy" />
        <span>
          I understand my old encryption passphrase will stop working as soon as this
          completes. My files and shares are not affected.
        </span>
      </label>

      <p v-if="errorMessage" class="text-sm text-destructive">{{ errorMessage }}</p>

      <button
        type="submit"
        :disabled="busy"
        class="inline-flex h-10 items-center gap-2 rounded-md bg-primary px-4 text-sm text-primary-foreground transition-colors hover:bg-primary/90 disabled:opacity-50"
      >
        <Loader2 v-if="busy" class="h-4 w-4 animate-spin" />
        {{ busy ? 'Resetting…' : 'Reset passphrase' }}
      </button>
      <p v-if="busy" class="text-xs text-muted-foreground">
        Deriving the new key takes a moment on purpose: the same cost that slows this down slows
        an attacker guessing the passphrase offline.
      </p>
    </form>
  </div>
</template>
