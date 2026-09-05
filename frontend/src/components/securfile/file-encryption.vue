<script setup lang="ts">
import { Check, FileIcon, Lock, RefreshCw, Upload, X } from 'lucide-vue-next'
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { fileApi } from '@/api/file_api'
import { MAX_UPLOAD_SIZE_BYTES, formatFileSize } from '@/api/types'

interface UploadedFile {
  raw: File
  name: string
  size: number
  type: string
}

const maxUploadLabel = formatFileSize(MAX_UPLOAD_SIZE_BYTES)

const router = useRouter()
const files = ref<UploadedFile[]>([])
const isEncrypting = ref(false)
const isEncrypted = ref(false)
const errorMessage = ref('')
const dragActive = ref(false)
const algorithms = ['AES-128', 'AES-192', 'AES-256', '3DES'] as const
const selectedAlgorithm = ref<(typeof algorithms)[number]>('AES-256')

const toUploadedFile = (file: File): UploadedFile => ({
  raw: file,
  name: file.name,
  size: file.size,
  type: file.type || 'unknown',
})

const addFiles = (fileList: FileList) => {
  files.value = [...files.value, ...Array.from(fileList, toUploadedFile)]
  isEncrypted.value = false
  errorMessage.value = ''
}

const handleDrag = (e: DragEvent) => {
  e.preventDefault()
  e.stopPropagation()
  dragActive.value = e.type === 'dragenter' || e.type === 'dragover'
}

const handleDrop = (e: DragEvent) => {
  e.preventDefault()
  e.stopPropagation()
  dragActive.value = false
  if (!e.dataTransfer?.files?.length) return
  addFiles(e.dataTransfer.files)
}

const handleFileInput = (e: Event) => {
  const target = e.target as HTMLInputElement
  if (!target.files?.length) return
  addFiles(target.files)
}

const removeFile = (index: number) => {
  files.value = files.value.filter((_, i) => i !== index)
  isEncrypted.value = false
}

const handleEncrypt = async () => {
  if (!files.value.length) return
  isEncrypting.value = true
  errorMessage.value = ''
  try {
    for (const file of files.value) {
      await fileApi.upload(file.raw)
    }
    isEncrypted.value = true
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Upload failed'
    isEncrypted.value = false
  } finally {
    isEncrypting.value = false
  }
}

const goToFiles = () => {
  router.push('/files')
}
</script>

<template>
  <section id="encrypt" class="py-20">
    <div class="container mx-auto px-4">
      <div class="text-center mb-16">
        <h2 class="text-3xl md:text-4xl font-bold text-foreground mb-4">Encrypt Your Files</h2>
        <p class="text-muted-foreground max-w-2xl mx-auto text-pretty">Upload files and encrypt with one click. Server-side encryption uses AES-256-GCM. Files up to {{ maxUploadLabel }} are supported.</p>
      </div>
      <div class="max-w-4xl mx-auto rounded-xl bg-card border border-border p-6">
        <div class="grid lg:grid-cols-2 gap-8">
          <div>
            <label class="text-foreground mb-4 block text-lg font-medium">Upload Files</label>
            <div
              :class="`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${dragActive ? 'border-primary bg-primary/5' : 'border-border hover:border-primary/50'}`"
              @dragenter="handleDrag"
              @dragleave="handleDrag"
              @dragover="handleDrag"
              @drop="handleDrop"
            >
              <Upload class="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <p class="text-foreground mb-2">Drag files here</p>
              <p class="text-muted-foreground text-sm mb-4">or</p>
              <label class="inline-flex h-9 px-4 items-center rounded-md border border-border cursor-pointer hover:bg-secondary transition-colors">
                <input type="file" multiple class="hidden" @change="handleFileInput" />
                <span>Select Files</span>
              </label>
              <p class="text-muted-foreground text-xs mt-4">Up to {{ maxUploadLabel }} per file</p>
            </div>
            <div v-if="files.length" class="mt-4 space-y-2">
              <div v-for="(file, index) in files" :key="`${file.name}-${index}`" class="flex items-center justify-between p-3 rounded-lg bg-secondary/50">
                <div class="flex items-center gap-3">
                  <FileIcon class="h-5 w-5 text-primary" />
                  <div>
                    <p class="text-sm text-foreground truncate max-w-[200px]">{{ file.name }}</p>
                    <p class="text-xs text-muted-foreground">{{ formatFileSize(file.size) }}</p>
                  </div>
                </div>
                <button class="h-8 w-8 inline-flex items-center justify-center rounded-md hover:bg-secondary" @click="removeFile(index)">
                  <X class="h-4 w-4" />
                </button>
              </div>
            </div>
          </div>

          <div>
            <label class="text-foreground mb-4 block text-lg font-medium">Encryption Model</label>
            <div class="space-y-4">
              <select
                v-model="selectedAlgorithm"
                class="h-10 w-full rounded-md border border-border bg-secondary px-3 text-foreground"
                @change="isEncrypted = false"
              >
                <option v-for="algorithm in algorithms" :key="algorithm" :value="algorithm">
                  {{ algorithm }}
                </option>
              </select>
              <p class="text-xs text-muted-foreground">
                Backend currently encrypts with AES-256-GCM. Algorithm selection is for display only.
              </p>
              <div class="p-3 rounded-lg bg-secondary/50 border border-border">
                <p class="text-sm text-foreground">
                  Selected model: <span class="font-semibold text-primary">{{ selectedAlgorithm }}</span>
                </p>
              </div>
            </div>

            <div class="mt-8">
              <button :disabled="!files.length || isEncrypting" class="w-full h-11 inline-flex items-center justify-center gap-2 rounded-md bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50" @click="handleEncrypt">
                <template v-if="isEncrypting"><RefreshCw class="h-4 w-4 animate-spin" /> Encrypting...</template>
                <template v-else-if="isEncrypted"><Check class="h-4 w-4" /> Encryption Complete</template>
                <template v-else><Lock class="h-4 w-4" /> Start Encryption</template>
              </button>
              <button v-if="isEncrypted" class="w-full h-11 mt-4 inline-flex items-center justify-center gap-2 rounded-md border border-border hover:bg-secondary" @click="goToFiles">
                View Encrypted Files
              </button>
              <p v-if="errorMessage" class="text-sm text-destructive mt-3">{{ errorMessage }}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
