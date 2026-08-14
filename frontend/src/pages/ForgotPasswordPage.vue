<script setup lang="ts">
import { ref } from 'vue'
import { RouterLink } from 'vue-router'
import { KeyRound } from 'lucide-vue-next'

const username = ref('')
const email = ref('')
const password = ref('')
const confirmPassword = ref('')
</script>

<template>
  <section class="min-h-[80vh] flex items-center justify-center px-4 py-20">
    <div class="w-full max-w-md rounded-xl border border-border bg-card p-8">
      <div class="flex items-center gap-2 mb-6">
        <div class="p-2 rounded-lg bg-primary/10">
          <KeyRound class="h-5 w-5 text-primary" />
        </div>
        <h1 class="text-2xl font-bold text-foreground">Reset Password</h1>
      </div>

      <p class="text-sm text-muted-foreground mb-6">
        Verify your account with username and email, then set a new password.
      </p>

      <form @submit.prevent>
        <label class="text-sm text-foreground mb-2 block">
          Username <span class="text-destructive">*</span>
        </label>
        <input
          v-model="username"
          placeholder="Username"
          required
          class="h-10 w-full rounded-md border border-border bg-secondary px-3 mb-4"
        />

        <label class="text-sm text-foreground mb-2 block">
          Email <span class="text-destructive">*</span>
        </label>
        <input
          v-model="email"
          placeholder="Email"
          type="email"
          required
          class="h-10 w-full rounded-md border border-border bg-secondary px-3 mb-4"
        />

        <label class="text-sm text-foreground mb-2 block">
          New Password <span class="text-destructive">*</span>
        </label>
        <input
          v-model="password"
          placeholder="New password"
          type="password"
          required
          class="h-10 w-full rounded-md border border-border bg-secondary px-3 mb-4"
        />

        <label class="text-sm text-foreground mb-2 block">
          Confirm New Password <span class="text-destructive">*</span>
        </label>
        <input
          v-model="confirmPassword"
          placeholder="Confirm new password"
          type="password"
          required
          class="h-10 w-full rounded-md border border-border bg-secondary px-3 mb-6"
        />

        <button
          type="button"
          disabled
          class="w-full h-11 rounded-md bg-muted text-muted-foreground cursor-not-allowed"
        >
          Under development, not available yet
        </button>
      </form>

      <p class="text-sm text-muted-foreground mt-6 text-center">
        Remember your password?
        <RouterLink to="/login" class="text-primary hover:underline">Sign in</RouterLink>
      </p>
    </div>
  </section>
</template>
