<template>
  <section class="card">
    <h1>Register</h1>
    <input v-model="username" placeholder="Username" />
    <input v-model="email" placeholder="Email" />
    <input v-model="password" placeholder="Password" type="password" />
    <button @click="register">Register</button>
  </section>

  <section v-if="privateKey" class="card">
    <h2>Private Key</h2>
    <p>Demo only: user should download and store this private key safely.</p>
    <textarea :value="privateKey" rows="12" readonly />
  </section>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { authApi } from '../api/auth_api'

const username = ref('')
const email = ref('')
const password = ref('')
const privateKey = ref('')

async function register() {
  const res = await authApi.register({ username: username.value, email: email.value, password: password.value })
  privateKey.value = res.data?.data?.private_key_pem || ''
}
</script>
