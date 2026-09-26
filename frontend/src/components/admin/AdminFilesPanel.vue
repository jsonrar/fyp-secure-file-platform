<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RefreshCw } from 'lucide-vue-next'

import { adminApi, type AdminFileOut } from '@/api/admin_api'
import { apiErrorMessage } from '@/api/http'
import { formatFileSize, unwrapData } from '@/api/types'

const files = ref<AdminFileOut[]>([])
const isLoading = ref(false)
const errorMessage = ref('')
const hasMore = ref(false)
const offset = ref(0)
const LIMIT = 50

function formatTimestamp(value: string): string {
  const parsed = new Date(value)
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString()
}

async function load(reset = true) {
  isLoading.value = true
  errorMessage.value = ''
  if (reset) offset.value = 0
  try {
    const data = unwrapData(await adminApi.listFiles({ limit: LIMIT, offset: offset.value }))
    files.value = reset ? data.files : [...files.value, ...data.files]
    hasMore.value = data.has_more
  } catch (error) {
    errorMessage.value = apiErrorMessage(error, 'Failed to load files')
  } finally {
    isLoading.value = false
  }
}

async function loadMore() {
  offset.value += LIMIT
  await load(false)
}

onMounted(() => {
  void load()
})
</script>

<template>
  <div>
    <div class="mb-4 flex flex-wrap items-center justify-between gap-3">
      <div>
        <h2 class="text-lg font-semibold text-foreground">All files</h2>
        <p class="text-sm text-muted-foreground">
          Metadata only — ciphertext stays opaque. Admins cannot decrypt user files from this panel.
        </p>
      </div>
      <button
        type="button"
        class="inline-flex h-9 items-center gap-2 rounded-md border border-border px-3 text-sm hover:bg-secondary"
        :disabled="isLoading"
        @click="load()"
      >
        <RefreshCw class="h-4 w-4" :class="{ 'animate-spin': isLoading }" />
        Refresh
      </button>
    </div>

    <p v-if="errorMessage" class="mb-3 text-sm text-destructive" role="alert">{{ errorMessage }}</p>

    <div v-if="isLoading && !files.length" class="py-10 text-center text-sm text-muted-foreground">
      Loading files…
    </div>
    <div v-else-if="!files.length" class="py-10 text-center text-sm text-muted-foreground">
      No files found.
    </div>
    <div v-else class="overflow-x-auto rounded-xl border border-border">
      <table class="w-full min-w-[44rem] text-left text-sm">
        <thead class="border-b border-border bg-secondary/40 text-xs uppercase tracking-wide text-muted-foreground">
          <tr>
            <th class="px-4 py-3 font-medium">Filename</th>
            <th class="px-4 py-3 font-medium">Owner</th>
            <th class="px-4 py-3 font-medium">Size</th>
            <th class="px-4 py-3 font-medium">Status</th>
            <th class="px-4 py-3 font-medium">Updated</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="file in files"
            :key="file.file_id"
            class="border-b border-border last:border-0"
          >
            <td class="max-w-[16rem] truncate px-4 py-3 font-medium text-foreground" :title="file.original_filename">
              {{ file.original_filename }}
            </td>
            <td class="px-4 py-3 text-muted-foreground">{{ file.owner_username }}</td>
            <td class="px-4 py-3 text-muted-foreground">{{ formatFileSize(file.file_size) }}</td>
            <td class="px-4 py-3">
              <span class="rounded-full bg-secondary px-2 py-0.5 text-xs font-medium text-foreground">
                {{ file.status }}
              </span>
            </td>
            <td class="px-4 py-3 text-muted-foreground">{{ formatTimestamp(file.updated_at) }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="hasMore" class="mt-4 text-center">
      <button
        type="button"
        class="h-9 rounded-md border border-border px-4 text-sm hover:bg-secondary disabled:opacity-50"
        :disabled="isLoading"
        @click="loadMore"
      >
        Load more
      </button>
    </div>
  </div>
</template>
