<template>
  <section class="card">
    <h1>Upload File</h1>
    <input type="file" @change="onFileChange" />
    <button :disabled="!selectedFile" @click="upload">Upload and Encrypt</button>
  </section>

  <section v-if="result" class="card">
    <h2>Upload Result</h2>
    <pre>{{ result }}</pre>
  </section>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { fileApi } from '../api/file_api'

const selectedFile = ref<File | null>(null)
const result = ref('')

function onFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  selectedFile.value = input.files?.[0] || null
}

async function upload() {
  if (!selectedFile.value) return
  const res = await fileApi.upload(selectedFile.value)
  result.value = JSON.stringify(res.data, null, 2)
}
</script>
