<template>
  <section class="card">
    <h1>Login</h1>
    <input v-model="username" placeholder="Username" />
    <input v-model="password" placeholder="Password" type="password" />
    <button @click="login">Login</button>
  </section>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { authApi } from '../api/auth_api'
import { useAuthStore } from '../stores/auth_store'

const username = ref('')
const password = ref('')
const auth = useAuthStore()

async function login() {
  const res = await authApi.login({ username: username.value, password: password.value })
  const token = res.data?.data?.access_token || 'demo-token'
  auth.setToken(token)
}
</script>
