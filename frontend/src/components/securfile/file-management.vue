<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { AlertCircle, CheckCircle, Download, FileIcon, Filter, RefreshCw, Search, Shield, Share2, Trash2 } from 'lucide-vue-next'
import { fileApi } from '@/api/file_api'
import { formatFileSize, mapFileStatus, unwrapData } from '@/api/types'
import type { FileOut } from '@/api/types'
import ShareDialog from '@/components/ShareDialog.vue'

interface EncryptedFile {
  id: number
  name: string
  originalSize: string
  encryptedSize: string
  encryptedAt: string
  status: 'verified' | 'modified' | 'pending'
}

interface StatusConfig {
  label: string
  icon: typeof CheckCircle
  className: string
}

const searchQuery = ref('')
const files = ref<EncryptedFile[]>([])
const isLoading = ref(false)
const errorMessage = ref('')
const shareFileId = ref<number | null>(null)
const actionMessage = ref('')

const mapFile = (file: FileOut): EncryptedFile => ({
  id: file.file_id,
  name: file.original_filename,
  originalSize: formatFileSize(file.file_size),
  encryptedSize: formatFileSize(file.file_size),
  encryptedAt: '-',
  status: mapFileStatus(file.status),
})

const loadFiles = async () => {
  isLoading.value = true
  errorMessage.value = ''
  try {
    const res = await fileApi.listFiles()
    const data = unwrapData(res)
    const list = Array.isArray(data) ? data : data.files ?? []
    files.value = list.map(mapFile)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Failed to load files'
  } finally {
    isLoading.value = false
  }
}

onMounted(loadFiles)

const filteredFiles = computed(() =>
  files.value.filter((file) => file.name.toLowerCase().includes(searchQuery.value.toLowerCase())),
)

const handleDelete = async (id: number) => {
  actionMessage.value = ''
  try {
    await fileApi.delete(id)
    files.value = files.value.filter((f) => f.id !== id)
    actionMessage.value = 'File deleted'
  } catch (error) {
    actionMessage.value = error instanceof Error ? error.message : 'Delete failed'
  }
}

const handleDownload = async (id: number) => {
  actionMessage.value = ''
  try {
    await fileApi.download(id)
    actionMessage.value = 'Download request sent'
  } catch (error) {
    actionMessage.value = error instanceof Error ? error.message : 'Download failed'
  }
}

const handleIntegrityCheck = async (id: number) => {
  actionMessage.value = ''
  try {
    const res = await fileApi.integrityCheck(id)
    const data = unwrapData(res) as { status?: string }
    const file = files.value.find((f) => f.id === id)
    if (file && data.status) {
      file.status = mapFileStatus(data.status)
    }
    actionMessage.value = `Integrity check: ${data.status ?? 'done'}`
  } catch (error) {
    actionMessage.value = error instanceof Error ? error.message : 'Integrity check failed'
  }
}

const openShare = (id: number) => {
  shareFileId.value = id
}

const closeShare = () => {
  shareFileId.value = null
}

const statusConfig: Record<EncryptedFile['status'], StatusConfig> = {
  verified: { label: 'Verified', icon: CheckCircle, className: 'bg-primary/10 text-primary' },
  modified: { label: 'Modified', icon: AlertCircle, className: 'bg-destructive/10 text-destructive' },
  pending: { label: 'Pending', icon: Shield, className: 'bg-muted text-muted-foreground' },
}
</script>

<template>
  <section id="manage" class="py-20 bg-transparent">
    <div class="container mx-auto px-4">
      <div class="text-center mb-16">
        <h2 class="text-3xl md:text-4xl font-bold text-foreground mb-4">Manage Encrypted Files</h2>
        <p class="text-muted-foreground max-w-2xl mx-auto text-pretty">View, download, share, and verify all your encrypted files</p>
      </div>

      <div class="bg-card border border-border rounded-xl max-w-6xl mx-auto p-6">
        <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
          <div>
            <h3 class="text-foreground text-lg font-semibold">My Encrypted Files</h3>
            <p class="text-muted-foreground text-sm">Total {{ filteredFiles.length }} encrypted files</p>
          </div>
          <div class="flex items-center gap-2">
            <div class="relative">
              <Search class="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <input v-model="searchQuery" placeholder="Search files..." class="h-10 w-full md:w-64 rounded-md border border-border bg-secondary pl-9 pr-3" />
            </div>
            <button class="h-10 w-10 inline-flex items-center justify-center rounded-md border border-border hover:bg-secondary" @click="loadFiles">
              <RefreshCw class="h-4 w-4" :class="{ 'animate-spin': isLoading }" />
            </button>
            <button class="h-10 w-10 inline-flex items-center justify-center rounded-md border border-border hover:bg-secondary"><Filter class="h-4 w-4" /></button>
          </div>
        </div>

        <p v-if="errorMessage" class="text-sm text-destructive mb-4">{{ errorMessage }}</p>
        <p v-if="actionMessage" class="text-sm text-primary mb-4">{{ actionMessage }}</p>

        <div v-if="isLoading && !files.length" class="text-center py-12 text-muted-foreground">
          Loading files...
        </div>

        <div v-else-if="!filteredFiles.length" class="text-center py-12 text-muted-foreground">
          No encrypted files yet. Upload your first file to get started.
        </div>

        <div v-else class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-border text-muted-foreground">
                <th class="text-left py-3">File Name</th>
                <th class="text-left py-3 hidden md:table-cell">Original Size</th>
                <th class="text-left py-3 hidden md:table-cell">Encrypted Size</th>
                <th class="text-left py-3 hidden lg:table-cell">Encrypted At</th>
                <th class="text-left py-3">Status</th>
                <th class="text-right py-3">Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="file in filteredFiles" :key="file.id" class="border-b border-border/60">
                <td class="py-3">
                  <div class="flex items-center gap-3">
                    <div class="p-2 rounded-lg bg-secondary"><FileIcon class="h-4 w-4 text-primary" /></div>
                    <div>
                      <p class="text-foreground font-medium">{{ file.name }}</p>
                      <p class="text-xs text-muted-foreground md:hidden">{{ file.originalSize }} -> {{ file.encryptedSize }}</p>
                    </div>
                  </div>
                </td>
                <td class="text-muted-foreground hidden md:table-cell">{{ file.originalSize }}</td>
                <td class="text-muted-foreground hidden md:table-cell">{{ file.encryptedSize }}</td>
                <td class="text-muted-foreground hidden lg:table-cell">{{ file.encryptedAt }}</td>
                <td>
                  <button class="inline-flex items-center gap-1 px-2 py-1 rounded-md" :class="statusConfig[file.status].className" @click="handleIntegrityCheck(file.id)">
                    <component :is="statusConfig[file.status].icon" class="h-3 w-3" />
                    {{ statusConfig[file.status].label }}
                  </button>
                </td>
                <td class="text-right">
                  <div class="inline-flex gap-1">
                    <button class="h-8 w-8 inline-flex items-center justify-center rounded-md hover:bg-secondary" title="Download" @click="handleDownload(file.id)">
                      <Download class="h-4 w-4" />
                    </button>
                    <button class="h-8 w-8 inline-flex items-center justify-center rounded-md hover:bg-secondary" title="Share" @click="openShare(file.id)">
                      <Share2 class="h-4 w-4" />
                    </button>
                    <button class="h-8 w-8 inline-flex items-center justify-center rounded-md hover:bg-secondary text-destructive" title="Delete" @click="handleDelete(file.id)">
                      <Trash2 class="h-4 w-4" />
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <ShareDialog v-if="shareFileId !== null" :file-id="shareFileId" @close="closeShare" />
  </section>
</template>
