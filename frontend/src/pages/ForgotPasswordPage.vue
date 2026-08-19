<script setup lang="ts">
import { computed, onUnmounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { CheckCircle2, Info, KeyRound } from 'lucide-vue-next'
import { authApi } from '@/api/auth_api'
import { apiErrorMessage } from '@/api/http'

const PASSWORD_MIN_LENGTH = 15

const username = ref('')
const email = ref('')
const verificationCode = ref('')
const password = ref('')
const confirmPassword = ref('')

const errorMessage = ref('')
const codeNotice = ref('')
const isSendingCode = ref(false)
const isSubmitting = ref(false)
const cooldownSeconds = ref(0)
let cooldownTimer: ReturnType<typeof setInterval> | undefined

const isComplete = ref(false)
const revokedSessions = ref(0)

const emailLooksValid = computed(() => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.value.trim()))
const passwordTooShort = computed(
  () => password.value.length > 0 && password.value.length < PASSWORD_MIN_LENGTH,
)
const passwordsMismatch = computed(
  () => confirmPassword.value.length > 0 && password.value !== confirmPassword.value,
)
const canSendCode = computed(
  () => emailLooksValid.value && cooldownSeconds.value === 0 && !isSendingCode.value,
)
const canSubmit = computed(
  () =>
    username.value.trim().length >= 3 &&
    emailLooksValid.value &&
    /^\d{6}$/.test(verificationCode.value.trim()) &&
    password.value.length >= PASSWORD_MIN_LENGTH &&
    password.value === confirmPassword.value &&
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
      purpose: 'PASSWORD_RESET',
    })
    const data = response.data.data
    const minutes = Math.max(1, Math.round(data.expires_in_seconds / 60))
    codeNotice.value = `If an account uses ${email.value.trim()}, a code is on its way. It expires in ${minutes} minutes.`
    startCooldown(data.resend_available_in_seconds)
  } catch (error) {
    errorMessage.value = apiErrorMessage(error, 'Could not send the verification code')
  } finally {
    isSendingCode.value = false
  }
}

async function resetPassword() {
  if (!canSubmit.value) return
  isSubmitting.value = true
  errorMessage.value = ''
  codeNotice.value = ''
  try {
    const response = await authApi.resetPassword({
      username: username.value.trim(),
      email: email.value.trim(),
      verification_code: verificationCode.value.trim(),
      new_password: password.value,
    })
    revokedSessions.value = response.data.data.revoked_sessions
    isComplete.value = true
    password.value = ''
    confirmPassword.value = ''
    verificationCode.value = ''
  } catch (error) {
    errorMessage.value = apiErrorMessage(error, 'Password reset failed')
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <section class="min-h-[80vh] flex items-center justify-center px-4 py-20">
    <div class="w-full max-w-md rounded-xl border border-border bg-card p-8">
      <template v-if="!isComplete">
        <div class="flex items-center gap-2 mb-6">
          <div class="p-2 rounded-lg bg-primary/10">
            <KeyRound class="h-5 w-5 text-primary" />
          </div>
          <h1 class="text-2xl font-bold text-foreground">Reset Password</h1>
        </div>

        <p class="text-sm text-muted-foreground mb-6">
          Verify your account with your username and email, confirm the emailed code, then set a
          new password.
        </p>

        <form @submit.prevent="resetPassword">
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
            Email <span class="text-destructive">*</span>
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
          <div class="flex gap-2 mb-4">
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

          <label class="text-sm text-foreground mb-2 block">
            New Password <span class="text-destructive">*</span>
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
            Confirm New Password <span class="text-destructive">*</span>
          </label>
          <input
            v-model="confirmPassword"
            placeholder="Repeat your new password"
            type="password"
            required
            autocomplete="new-password"
            class="h-10 w-full rounded-md border border-border bg-secondary px-3"
          />
          <p v-if="passwordsMismatch" class="text-xs text-destructive mt-1">
            The two passwords do not match.
          </p>
          <div class="mb-4" />

          <p class="text-xs text-muted-foreground mb-6 flex gap-1.5">
            <Info class="h-4 w-4 shrink-0 text-primary" />
            <span>
              This changes your login password only. Your encryption passphrase and private key are
              unaffected, so your encrypted files stay accessible.
            </span>
          </p>

          <button
            type="submit"
            class="w-full h-11 rounded-md bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed"
            :disabled="!canSubmit"
          >
            {{ isSubmitting ? 'Resetting password...' : 'Reset password' }}
          </button>
        </form>

        <p v-if="codeNotice" class="text-xs text-muted-foreground mt-3">{{ codeNotice }}</p>
        <p v-if="errorMessage" class="text-sm text-destructive mt-3">{{ errorMessage }}</p>

        <p class="text-sm text-muted-foreground mt-6 text-center">
          Remember your password?
          <RouterLink to="/login" class="text-primary hover:underline">Sign in</RouterLink>
        </p>
      </template>

      <template v-else>
        <div class="flex items-center gap-2 mb-4">
          <div class="p-2 rounded-lg bg-primary/10">
            <CheckCircle2 class="h-5 w-5 text-primary" />
          </div>
          <h1 class="text-2xl font-bold text-foreground">Password Reset</h1>
        </div>

        <p class="text-sm text-muted-foreground">
          Your password has been updated. Sign in with the new password.
        </p>
        <p v-if="revokedSessions > 0" class="text-sm text-muted-foreground mt-2">
          {{ revokedSessions }} other active
          {{ revokedSessions === 1 ? 'session was' : 'sessions were' }} signed out for safety.
        </p>

        <RouterLink
          to="/login"
          class="mt-6 w-full h-11 rounded-md bg-primary text-primary-foreground hover:bg-primary/90 flex items-center justify-center"
        >
          Continue to sign in
        </RouterLink>
      </template>
    </div>
  </section>
</template>
