<script setup lang="ts">
import { computed, onUnmounted, reactive, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { CheckCircle2, Info, KeyRound } from 'lucide-vue-next'
import { authApi } from '@/api/auth_api'
import { apiErrorMessage } from '@/api/http'
import PasswordField from '@/components/PasswordField.vue'
import {
  PASSWORD_MIN_LENGTH,
  PASSWORD_REQUIREMENT_HINT,
  evaluatePassword,
} from '@/utils/password-policy'

const USERNAME_MIN_LENGTH = 3

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

// Same contract as registration: the submit button stays live and names the first
// field that still needs work, rather than going grey without saying why.
type FieldName = 'username' | 'email' | 'code' | 'password' | 'confirmPassword'

const touched = reactive<Record<FieldName, boolean>>({
  username: false,
  email: false,
  code: false,
  password: false,
  confirmPassword: false,
})
const hasAttemptedSubmit = ref(false)

const usernameInput = ref<HTMLInputElement | null>(null)
const emailInput = ref<HTMLInputElement | null>(null)
const codeInput = ref<HTMLInputElement | null>(null)
const passwordField = ref<InstanceType<typeof PasswordField> | null>(null)
const confirmPasswordField = ref<InstanceType<typeof PasswordField> | null>(null)

const emailLooksValid = computed(() => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.value.trim()))

const errors = computed<Record<FieldName, string>>(() => {
  let confirmError = ''
  if (confirmPassword.value.length === 0) {
    confirmError = 'Repeat your new password.'
  } else if (confirmPassword.value !== password.value) {
    confirmError = 'The two passwords do not match.'
  }

  return {
    username:
      username.value.trim().length >= USERNAME_MIN_LENGTH
        ? ''
        : `Use at least ${USERNAME_MIN_LENGTH} characters.`,
    email: emailLooksValid.value ? '' : 'Enter a valid email address.',
    code: /^\d{6}$/.test(verificationCode.value.trim())
      ? ''
      : 'Enter the 6-digit code sent to your email.',
    password: evaluatePassword(password.value, [username.value.trim(), email.value.trim()]).message,
    confirmPassword: confirmError,
  }
})

/** Field order here is the order on screen, so "first problem" means the top one. */
const FIELD_ORDER: readonly FieldName[] = [
  'username',
  'email',
  'code',
  'password',
  'confirmPassword',
]

function errorFor(field: FieldName): string {
  if (!hasAttemptedSubmit.value && !touched[field]) return ''
  return errors.value[field]
}

function markTouched(field: FieldName) {
  touched[field] = true
}

function focusField(field: FieldName) {
  const targets: Record<FieldName, { focus: () => void } | null> = {
    username: usernameInput.value,
    email: emailInput.value,
    code: codeInput.value,
    password: passwordField.value,
    confirmPassword: confirmPasswordField.value,
  }
  targets[field]?.focus()
}

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
  if (isSendingCode.value || cooldownSeconds.value > 0) return
  if (!emailLooksValid.value) {
    markTouched('email')
    focusField('email')
    return
  }
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
  if (isSubmitting.value) return

  hasAttemptedSubmit.value = true
  const firstInvalid = FIELD_ORDER.find((field) => errors.value[field] !== '')
  if (firstInvalid) {
    errorMessage.value = 'Some details still need fixing. See the messages above.'
    focusField(firstInvalid)
    return
  }

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

        <form novalidate @submit.prevent="resetPassword">
          <label for="reset-username" class="text-sm text-foreground mb-2 block">
            Username <span class="text-destructive">*</span>
          </label>
          <input
            id="reset-username"
            ref="usernameInput"
            v-model="username"
            placeholder="Username"
            autocomplete="username"
            :aria-invalid="errorFor('username') ? 'true' : undefined"
            class="h-10 w-full rounded-md border bg-secondary px-3 text-foreground"
            :class="errorFor('username') ? 'border-destructive' : 'border-border'"
            @blur="markTouched('username')"
          />
          <p v-if="errorFor('username')" class="text-xs text-destructive mt-1" role="alert">
            {{ errorFor('username') }}
          </p>
          <div class="mb-4" />

          <label for="reset-email" class="text-sm text-foreground mb-2 block">
            Email <span class="text-destructive">*</span>
          </label>
          <input
            id="reset-email"
            ref="emailInput"
            v-model="email"
            placeholder="you@example.com"
            type="email"
            autocomplete="email"
            :aria-invalid="errorFor('email') ? 'true' : undefined"
            class="h-10 w-full rounded-md border bg-secondary px-3 text-foreground"
            :class="errorFor('email') ? 'border-destructive' : 'border-border'"
            @blur="markTouched('email')"
          />
          <p v-if="errorFor('email')" class="text-xs text-destructive mt-1" role="alert">
            {{ errorFor('email') }}
          </p>
          <div class="mb-4" />

          <label for="reset-code" class="text-sm text-foreground mb-2 block">
            Verification Code <span class="text-destructive">*</span>
          </label>
          <div class="flex gap-2">
            <input
              id="reset-code"
              ref="codeInput"
              v-model="verificationCode"
              placeholder="6-digit code"
              inputmode="numeric"
              maxlength="6"
              autocomplete="one-time-code"
              :aria-invalid="errorFor('code') ? 'true' : undefined"
              class="h-10 flex-1 rounded-md border bg-secondary px-3 text-foreground tracking-widest"
              :class="errorFor('code') ? 'border-destructive' : 'border-border'"
              @blur="markTouched('code')"
            />
            <button
              type="button"
              class="h-10 shrink-0 rounded-md border border-border px-3 text-sm text-foreground hover:bg-secondary disabled:opacity-50 disabled:cursor-not-allowed"
              :disabled="isSendingCode || cooldownSeconds > 0"
              @click="sendCode"
            >
              <span v-if="isSendingCode">Sending...</span>
              <span v-else-if="cooldownSeconds > 0">Resend in {{ cooldownSeconds }}s</span>
              <span v-else>Send code</span>
            </button>
          </div>
          <p v-if="errorFor('code')" class="text-xs text-destructive mt-1" role="alert">
            {{ errorFor('code') }}
          </p>
          <div class="mb-4" />

          <PasswordField
            ref="passwordField"
            v-model="password"
            label="New Password"
            :placeholder="`At least ${PASSWORD_MIN_LENGTH} characters`"
            :hint="PASSWORD_REQUIREMENT_HINT"
            :error="errorFor('password')"
            @blur="markTouched('password')"
          />
          <div class="mb-4" />

          <PasswordField
            ref="confirmPasswordField"
            v-model="confirmPassword"
            label="Confirm New Password"
            placeholder="Repeat your new password"
            :error="errorFor('confirmPassword')"
            @blur="markTouched('confirmPassword')"
          />
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
            :disabled="isSubmitting"
          >
            {{ isSubmitting ? 'Resetting password...' : 'Reset password' }}
          </button>
        </form>

        <p v-if="codeNotice" class="text-xs text-muted-foreground mt-3">{{ codeNotice }}</p>
        <p v-if="errorMessage" class="text-sm text-destructive mt-3" role="alert">
          {{ errorMessage }}
        </p>

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
