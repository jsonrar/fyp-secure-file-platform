<template>
  <section class="card">
    <h1>Files</h1>
    <p>Accessible encrypted files will be listed here.</p>
    <button @click="loadFiles">Refresh</button>
  </section>

  <section class="card">
    <pre>{{ files }}</pre>
  </section>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { fileApi } from '../api/file_api'

const files = ref('[]')

async function loadFiles() {
  const res = await fileApi.listFiles()
  files.value = JSON.stringify(res.data, null, 2)
}
</script>
