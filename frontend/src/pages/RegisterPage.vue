<script setup lang="ts">
import { computed, onUnmounted, reactive, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { Download, KeyRound, ShieldCheck, UserPlus } from 'lucide-vue-next'
import { authApi } from '@/api/auth_api'
import { apiErrorMessage } from '@/api/http'
import PasswordField from '@/components/PasswordField.vue'
import { enrolAccountKey } from '@/utils/account-crypto'

const route = useRoute()

// Arriving straight from a deletion. Saying so beats a bare registration form for someone
// who has just destroyed an account on purpose and is expecting to start over.
const afterDeletion = computed(() => route.query.deleted === '1')
import {
  PASSPHRASE_MIN_LENGTH,
  PASSWORD_MIN_LENGTH,
  PASSWORD_REQUIREMENT_HINT,
  evaluatePassword,
} from '@/utils/password-policy'

const USERNAME_MIN_LENGTH = 3
const USERNAME_MAX_LENGTH = 100
const USERNAME_PATTERN = /^[A-Za-z0-9_.-]+$/

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

/**
 * Registration validates on submit, not by disabling the button.
 *
 * A disabled Register button cannot explain itself: the user is left comparing
 * their password against a placeholder to guess which rule they missed. So the
 * button stays live, every rule is checked on click, and the first field that
 * fails is named and focused. A rule is also shown early once the user has left
 * that field, which is the point they have finished their thought about it.
 */
type FieldName = 'username' | 'password' | 'confirmPassword' | 'passphrase' | 'email' | 'code'

const touched = reactive<Record<FieldName, boolean>>({
  username: false,
  password: false,
  confirmPassword: false,
  passphrase: false,
  email: false,
  code: false,
})
const hasAttemptedSubmit = ref(false)

const usernameInput = ref<HTMLInputElement | null>(null)
const emailInput = ref<HTMLInputElement | null>(null)
const codeInput = ref<HTMLInputElement | null>(null)
const passwordField = ref<InstanceType<typeof PasswordField> | null>(null)
const confirmPasswordField = ref<InstanceType<typeof PasswordField> | null>(null)
const passphraseField = ref<InstanceType<typeof PasswordField> | null>(null)

const emailLooksValid = computed(() => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.value.trim()))

/** The password must not be built out of the account details it protects. */
const passwordCheck = computed(() =>
  evaluatePassword(password.value, [username.value.trim(), email.value.trim()]),
)

const errors = computed<Record<FieldName, string>>(() => {
  const trimmedUsername = username.value.trim()

  let usernameError = ''
  if (trimmedUsername.length < USERNAME_MIN_LENGTH) {
    usernameError = `Use at least ${USERNAME_MIN_LENGTH} characters.`
  } else if (trimmedUsername.length > USERNAME_MAX_LENGTH) {
    usernameError = `Use at most ${USERNAME_MAX_LENGTH} characters.`
  } else if (!USERNAME_PATTERN.test(trimmedUsername)) {
    usernameError = 'Use only letters, numbers, underscore, dot, and hyphen.'
  }

  let confirmError = ''
  if (confirmPassword.value.length === 0) {
    confirmError = 'Repeat your password.'
  } else if (confirmPassword.value !== password.value) {
    confirmError = 'The two passwords do not match.'
  }

  let passphraseError = ''
  const passphraseLength = [...passphrase.value].length
  if (passphraseLength === 0) {
    passphraseError = 'Enter an encryption passphrase.'
  } else if (passphraseLength < PASSPHRASE_MIN_LENGTH) {
    passphraseError = `Use at least ${PASSPHRASE_MIN_LENGTH} characters (${passphraseLength} so far).`
  } else if (passphrase.value === password.value) {
    passphraseError = 'Use a different value from your login password.'
  }

  return {
    username: usernameError,
    password: passwordCheck.value.message,
    confirmPassword: confirmError,
    passphrase: passphraseError,
    email: emailLooksValid.value ? '' : 'Enter a valid email address.',
    code: /^\d{6}$/.test(verificationCode.value.trim())
      ? ''
      : 'Enter the 6-digit code sent to your email.',
  }
})

/** Field order here is the order on screen, so "first problem" means the top one. */
const FIELD_ORDER: readonly FieldName[] = [
  'username',
  'password',
  'confirmPassword',
  'passphrase',
  'email',
  'code',
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
    password: passwordField.value,
    confirmPassword: confirmPasswordField.value,
    passphrase: passphraseField.value,
    email: emailInput.value,
    code: codeInput.value,
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
  // The same rule as Register: the button explains the problem instead of hiding it.
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

        <p
          v-if="afterDeletion"
          class="text-sm rounded-md border border-border bg-secondary/60 text-foreground px-3 py-2 mb-4"
        >
          Your previous account and its files were deleted. You can register again with the
          same username and email if you want them.
        </p>

        <form novalidate @submit.prevent="register">
          <label for="register-username" class="text-sm text-foreground mb-2 block">
            Username <span class="text-destructive">*</span>
          </label>
          <input
            id="register-username"
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

          <PasswordField
            ref="passwordField"
            v-model="password"
            label="Password"
            :placeholder="`At least ${PASSWORD_MIN_LENGTH} characters`"
            :hint="PASSWORD_REQUIREMENT_HINT"
            :error="errorFor('password')"
            @blur="markTouched('password')"
          />
          <div class="mb-4" />

          <PasswordField
            ref="confirmPasswordField"
            v-model="confirmPassword"
            label="Confirm Password"
            placeholder="Repeat your password"
            :error="errorFor('confirmPassword')"
            @blur="markTouched('confirmPassword')"
          />
          <div class="mb-4" />

          <PasswordField
            ref="passphraseField"
            v-model="passphrase"
            label="Encryption Passphrase"
            :placeholder="`At least ${PASSPHRASE_MIN_LENGTH} characters, different from your password`"
            :error="errorFor('passphrase')"
            @blur="markTouched('passphrase')"
          >
            <template #hint>
              <p class="text-xs text-muted-foreground mt-1 flex gap-1.5">
                <ShieldCheck class="h-4 w-4 shrink-0 text-primary" />
                <span>
                  This never leaves your browser. It unlocks your private key, so if you lose it
                  your encrypted files cannot be recovered. That is why it stays longer than your
                  login password.
                </span>
              </p>
            </template>
          </PasswordField>
          <div class="mb-4" />

          <label for="register-email" class="text-sm text-foreground mb-2 block">
            Email Address <span class="text-destructive">*</span>
          </label>
          <input
            id="register-email"
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

          <label for="register-code" class="text-sm text-foreground mb-2 block">
            Verification Code <span class="text-destructive">*</span>
          </label>
          <div class="flex gap-2">
            <input
              id="register-code"
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
          <p v-if="codeNotice" class="text-xs text-muted-foreground mt-1">{{ codeNotice }}</p>
          <div class="mb-6" />

          <button
            type="submit"
            class="w-full h-11 rounded-md bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed"
            :disabled="isSubmitting"
          >
            {{ progressLabel || 'Register' }}
          </button>
        </form>

        <p v-if="errorMessage" class="text-sm text-destructive mt-3" role="alert">
          {{ errorMessage }}
        </p>

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
          Your account is ready. This is your account's RSA private key — the key your files
          are encrypted to. It is shown once and is not stored anywhere in readable form on
          the server.
        </p>

        <p class="text-sm text-muted-foreground mb-4">
          <strong class="text-foreground">Save it.</strong> It is the only way back into your
          files if you forget your encryption passphrase: the passphrase cannot be reset, and
          neither the team nor the server holds anything that can open your files without one
          of the two. The download is a plain text <code class="text-xs">.pem</code> file —
          your computer may have no application associated with it, which is expected; any
          text editor can open it.
        </p>

        <p class="text-sm text-muted-foreground mb-4">
          Because it needs no passphrase, treat the file itself as the secret: anyone who
          holds it can decrypt your files. Keep it somewhere you would keep a password, not in
          your Downloads folder.
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
          <span>I have saved this private key somewhere safe. I understand it will not be shown again, and that without it a forgotten passphrase means losing access to my files.</span>
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
