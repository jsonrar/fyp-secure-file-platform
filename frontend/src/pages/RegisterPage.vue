<script setup lang="ts">
import { computed, onUnmounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { Download, KeyRound, ShieldCheck, UserPlus } from 'lucide-vue-next'
import { authApi } from '@/api/auth_api'
import { apiErrorMessage } from '@/api/http'
import { enrolAccountKey } from '@/utils/account-crypto'

const PASSWORD_MIN_LENGTH = 15

const username = ref('')
const email = ref('')
const password = ref('')
const confirmPassword = ref('')
const passphrase = ref('')
const verificationCode = ref('')

const errorMessage = ref('')
const codeNotice = ref('')
const isSendingCode = ref(false)
const isSubmitting = ref(false)
const progressLabel = ref('')
const cooldownSeconds = ref(0)
let cooldownTimer: ReturnType<typeof setInterval> | undefined

const privateKeyPem = ref('')
const publicKeyFingerprint = ref('')
const keyAcknowledged = ref(false)

const emailLooksValid = computed(() => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.value.trim()))
const passwordTooShort = computed(
  () => password.value.length > 0 && password.value.length < PASSWORD_MIN_LENGTH,
)
const passwordsMismatch = computed(
  () => confirmPassword.value.length > 0 && password.value !== confirmPassword.value,
)
const passphraseReused = computed(
  () => passphrase.value.length > 0 && passphrase.value === password.value,
)
const canSendCode = computed(
  () => emailLooksValid.value && cooldownSeconds.value === 0 && !isSendingCode.value,
)
const canSubmit = computed(
  () =>
    username.value.trim().length >= 3 &&
    emailLooksValid.value &&
    password.value.length >= PASSWORD_MIN_LENGTH &&
    password.value === confirmPassword.value &&
    passphrase.value.length >= PASSWORD_MIN_LENGTH &&
    !passphraseReused.value &&
    /^\d{6}$/.test(verificationCode.value.trim()) &&
    !isSubmitting.value,
)

function startCooldown(seconds: number) {
  cooldownSeconds.value = seconds
  clearInterval(cooldownTimer)
  cooldownTimer = setInterval(() => {
    cooldownSeconds.value -= 1
    if (cooldownSeconds.value <= 0) {
      clearInterval(cooldownTimer)
      cooldownSeconds.value = 0
    }
  }, 1000)
}

onUnmounted(() => clearInterval(cooldownTimer))

async function sendCode() {
  if (!canSendCode.value) return
  isSendingCode.value = true
  errorMessage.value = ''
  codeNotice.value = ''
  try {
    const response = await authApi.sendVerificationCode({
      email: email.value.trim(),
      purpose: 'REGISTRATION',
    })
    const data = response.data.data
    const minutes = Math.max(1, Math.round(data.expires_in_seconds / 60))
    codeNotice.value = `If ${email.value.trim()} is available, a code is on its way. It expires in ${minutes} minutes.`
    startCooldown(data.resend_available_in_seconds)
  } catch (error) {
    errorMessage.value = apiErrorMessage(error, 'Could not send the verification code')
  } finally {
    isSendingCode.value = false
  }
}

async function register() {
  if (!canSubmit.value) return
  isSubmitting.value = true
  errorMessage.value = ''
  codeNotice.value = ''
  try {
    // Generating a 3072-bit RSA key and running Argon2id takes a moment and
    // blocks the main thread, so the button reports each stage.
    progressLabel.value = 'Generating your account key...'
    const { keyMaterial, privateKeyPem: generatedPem } = await enrolAccountKey(passphrase.value)

    progressLabel.value = 'Creating your account...'
    const response = await authApi.register({
      username: username.value.trim(),
      email: email.value.trim(),
      password: password.value,
      verification_code: verificationCode.value.trim(),
      key_material: keyMaterial,
    })

    privateKeyPem.value = generatedPem
    publicKeyFingerprint.value = response.data.data.public_key_fingerprint
    // The passphrase has done its job; drop it from component state.
    passphrase.value = ''
    password.value = ''
    confirmPassword.value = ''
    verificationCode.value = ''
  } catch (error) {
    errorMessage.value = apiErrorMessage(error, 'Registration failed')
  } finally {
    isSubmitting.value = false
    progressLabel.value = ''
  }
}

function downloadPrivateKey() {
  const blob = new Blob([privateKeyPem.value], { type: 'application/x-pem-file' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `secureview-private-key-${username.value.trim() || 'account'}.pem`
  link.click()
  URL.revokeObjectURL(url)
}
</script>

<template>
  <section class="min-h-[80vh] flex items-center justify-center px-4 py-20">
    <div class="w-full max-w-md rounded-xl border border-border bg-card p-8">
      <template v-if="!privateKeyPem">
        <div class="flex items-center gap-2 mb-6">
          <div class="p-2 rounded-lg bg-primary/10">
            <UserPlus class="h-5 w-5 text-primary" />
          </div>
          <h1 class="text-2xl font-bold text-foreground">Create Account</h1>
        </div>

        <form @submit.prevent="register">
          <label class="text-sm text-foreground mb-2 block">
            Username <span class="text-destructive">*</span>
          </label>
          <input
            v-model="username"
            placeholder="Username"
            required
            minlength="3"
            autocomplete="username"
            class="h-10 w-full rounded-md border border-border bg-secondary px-3 mb-4"
          />

          <label class="text-sm text-foreground mb-2 block">
            Password <span class="text-destructive">*</span>
          </label>
          <input
            v-model="password"
            placeholder="At least 15 characters"
            type="password"
            required
            autocomplete="new-password"
            class="h-10 w-full rounded-md border border-border bg-secondary px-3"
          />
          <p v-if="passwordTooShort" class="text-xs text-destructive mt-1">
            Use at least {{ PASSWORD_MIN_LENGTH }} characters ({{ password.length }} so far).
          </p>
          <div class="mb-4" />

          <label class="text-sm text-foreground mb-2 block">
            Confirm Password <span class="text-destructive">*</span>
          </label>
          <input
            v-model="confirmPassword"
            placeholder="Repeat your password"
            type="password"
            required
            autocomplete="new-password"
            class="h-10 w-full rounded-md border border-border bg-secondary px-3"
          />
          <p v-if="passwordsMismatch" class="text-xs text-destructive mt-1">
            The two passwords do not match.
          </p>
          <div class="mb-4" />

          <label class="text-sm text-foreground mb-2 block">
            Encryption Passphrase <span class="text-destructive">*</span>
          </label>
          <input
            v-model="passphrase"
            placeholder="At least 15 characters, different from your password"
            type="password"
            required
            autocomplete="new-password"
            class="h-10 w-full rounded-md border border-border bg-secondary px-3"
          />
          <p class="text-xs text-muted-foreground mt-1 flex gap-1.5">
            <ShieldCheck class="h-4 w-4 shrink-0 text-primary" />
            <span>
              This never leaves your browser. It unlocks your private key, so if you lose it your
              encrypted files cannot be recovered.
            </span>
          </p>
          <p v-if="passphraseReused" class="text-xs text-destructive mt-1">
            Use a different value from your login password.
          </p>
          <div class="mb-4" />

          <label class="text-sm text-foreground mb-2 block">
            Email Address <span class="text-destructive">*</span>
          </label>
          <input
            v-model="email"
            placeholder="you@example.com"
            type="email"
            required
            autocomplete="email"
            class="h-10 w-full rounded-md border border-border bg-secondary px-3 mb-4"
          />

          <label class="text-sm text-foreground mb-2 block">
            Verification Code <span class="text-destructive">*</span>
          </label>
          <div class="flex gap-2 mb-2">
            <input
              v-model="verificationCode"
              placeholder="6-digit code"
              inputmode="numeric"
              pattern="\d{6}"
              maxlength="6"
              required
              autocomplete="one-time-code"
              class="h-10 flex-1 rounded-md border border-border bg-secondary px-3 tracking-widest"
            />
            <button
              type="button"
              class="h-10 shrink-0 rounded-md border border-border px-3 text-sm text-foreground hover:bg-secondary disabled:opacity-50 disabled:cursor-not-allowed"
              :disabled="!canSendCode"
              @click="sendCode"
            >
              <span v-if="isSendingCode">Sending...</span>
              <span v-else-if="cooldownSeconds > 0">Resend in {{ cooldownSeconds }}s</span>
              <span v-else>Send code</span>
            </button>
          </div>
          <p v-if="codeNotice" class="text-xs text-muted-foreground mb-4">{{ codeNotice }}</p>
          <div v-else class="mb-4" />

          <button
            type="submit"
            class="w-full h-11 rounded-md bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed"
            :disabled="!canSubmit"
          >
            {{ progressLabel || 'Register' }}
          </button>
        </form>

        <p v-if="errorMessage" class="text-sm text-destructive mt-3">{{ errorMessage }}</p>

        <p class="text-sm text-muted-foreground mt-6 text-center">
          Already have an account?
          <RouterLink to="/login" class="text-primary hover:underline">Sign in</RouterLink>
        </p>
      </template>

      <template v-else>
        <div class="flex items-center gap-2 mb-4">
          <div class="p-2 rounded-lg bg-primary/10">
            <KeyRound class="h-5 w-5 text-primary" />
          </div>
          <h1 class="text-2xl font-bold text-foreground">Save Your Private Key</h1>
        </div>

        <p class="text-sm text-muted-foreground mb-4">
          Your account is ready. This private key is shown once and is not stored anywhere in
          readable form on the server. Save it somewhere safe together with your encryption
          passphrase.
        </p>

        <textarea
          :value="privateKeyPem"
          rows="9"
          readonly
          class="w-full rounded-md border border-border bg-background p-3 text-xs font-mono"
        />

        <p class="text-xs text-muted-foreground mt-2 break-all">
          Public key fingerprint: <span class="font-mono">{{ publicKeyFingerprint }}</span>
        </p>

        <button
          type="button"
          class="mt-4 w-full h-10 rounded-md border border-border text-sm text-foreground hover:bg-secondary flex items-center justify-center gap-2"
          @click="downloadPrivateKey"
        >
          <Download class="h-4 w-4" />
          Download private key
        </button>

        <label class="flex items-start gap-2 mt-4 text-sm text-foreground">
          <input v-model="keyAcknowledged" type="checkbox" class="mt-1" />
          <span>I have saved this private key. I understand it will not be shown again.</span>
        </label>

        <RouterLink
          to="/login"
          class="mt-4 w-full h-11 rounded-md bg-primary text-primary-foreground hover:bg-primary/90 flex items-center justify-center"
          :class="keyAcknowledged ? '' : 'pointer-events-none opacity-50'"
        >
          Continue to sign in
        </RouterLink>
      </template>
    </div>
  </section>
</template>
