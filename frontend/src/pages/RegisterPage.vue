<script setup lang="ts">
import { ref } from 'vue'
import { RouterLink } from 'vue-router'
import { UserPlus } from 'lucide-vue-next'
import { authApi } from '@/api/auth_api'

const username = ref('')
const email = ref('')
const password = ref('')
const privateKey = ref('')
const errorMessage = ref('')
const isSubmitting = ref(false)

async function register() {
  isSubmitting.value = true
  errorMessage.value = ''
  try {
    const res = await authApi.register({
      username: username.value,
      email: email.value,
      password: password.value,
    })
    privateKey.value = res.data?.data?.private_key_pem || ''
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Registration failed'
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <section class="min-h-[80vh] flex items-center justify-center px-4 py-20">
    <div class="w-full max-w-md rounded-xl border border-border bg-card p-8">
      <div class="flex items-center gap-2 mb-6">
        <div class="p-2 rounded-lg bg-primary/10">
          <UserPlus class="h-5 w-5 text-primary" />
        </div>
        <h1 class="text-2xl font-bold text-foreground">Create Account</h1>
      </div>

      <label class="text-sm text-foreground mb-2 block">Username</label>
      <input v-model="username" placeholder="Username" class="h-10 w-full rounded-md border border-border bg-secondary px-3 mb-4" />

      <label class="text-sm text-foreground mb-2 block">Email</label>
      <input v-model="email" placeholder="Email" type="email" class="h-10 w-full rounded-md border border-border bg-secondary px-3 mb-4" />

      <label class="text-sm text-foreground mb-2 block">Password</label>
      <input v-model="password" placeholder="Password" type="password" class="h-10 w-full rounded-md border border-border bg-secondary px-3 mb-6" />

      <button
        class="w-full h-11 rounded-md bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
        :disabled="isSubmitting"
        @click="register"
      >
        {{ isSubmitting ? 'Creating account...' : 'Register' }}
      </button>

      <p v-if="errorMessage" class="text-sm text-destructive mt-3">{{ errorMessage }}</p>

      <div v-if="privateKey" class="mt-6 rounded-lg border border-border bg-secondary/40 p-4">
        <h2 class="text-sm font-semibold text-foreground mb-2">Private Key</h2>
        <p class="text-xs text-muted-foreground mb-3">Download and store this private key safely. It will not be shown again.</p>
        <textarea :value="privateKey" rows="8" readonly class="w-full rounded-md border border-border bg-background p-3 text-xs font-mono" />
      </div>

      <p class="text-sm text-muted-foreground mt-6 text-center">
        Already have an account?
        <RouterLink to="/login" class="text-primary hover:underline">Sign in</RouterLink>
      </p>
    </div>
  </section>
</template>
