<script setup lang="ts">
import { Check, FileIcon, Lock, RefreshCw, Upload, X } from 'lucide-vue-next'
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { apiErrorMessage } from '@/api/http'
import { formatFileSize } from '@/api/types'
import {
  encryptAndUpload,
  fetchUploadRecipients,
  MAX_UPLOAD_BYTES,
  type UploadRecipients,
} from '@/crypto/upload'

type UploadStatus = 'pending' | 'encrypting' | 'done' | 'failed'

interface UploadedFile {
  raw: File
  name: string
  size: number
  type: string
  status: UploadStatus
  error: string
}

const router = useRouter()
const files = ref<UploadedFile[]>([])
const isEncrypting = ref(false)
const isEncrypted = ref(false)
const errorMessage = ref('')
const dragActive = ref(false)
const recoveryFingerprint = ref('')

const toUploadedFile = (file: File): UploadedFile => ({
  raw: file,
  name: file.name,
  size: file.size,
  type: file.type || 'unknown',
  status: 'pending',
  error: '',
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

/**
 * Encrypt each file in the browser, then upload ciphertext only.
 *
 * The recipient public keys are fetched once for the whole batch rather than per file.
 * Each file reports its own outcome, because one rejected filename should not hide the
 * files that did upload.
 */
const handleEncrypt = async () => {
  if (!files.value.length) return
  isEncrypting.value = true
  errorMessage.value = ''
  isEncrypted.value = false

  let recipients: UploadRecipients
  try {
    recipients = await fetchUploadRecipients()
    recoveryFingerprint.value = recipients.recoveryKeyFingerprint
  } catch (error) {
    errorMessage.value = apiErrorMessage(error, 'Could not load the encryption keys')
    isEncrypting.value = false
    return
  }

  let failures = 0
  for (const file of files.value) {
    file.status = 'encrypting'
    file.error = ''
    try {
      await encryptAndUpload(file.raw, recipients)
      file.status = 'done'
    } catch (error) {
      failures += 1
      file.status = 'failed'
      file.error = apiErrorMessage(error, 'Encryption failed')
    }
  }

  isEncrypting.value = false
  isEncrypted.value = failures === 0
  if (failures > 0) {
    errorMessage.value = `${failures} of ${files.value.length} file(s) failed. See each file below.`
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
        <p class="text-muted-foreground max-w-2xl mx-auto text-pretty">Files are encrypted in your browser with AES-256-GCM. Only ciphertext is uploaded; the server never receives your file or its key.</p>
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
            </div>
            <div v-if="files.length" class="mt-4 space-y-2">
              <div v-for="(file, index) in files" :key="`${file.name}-${index}`" class="flex items-center justify-between p-3 rounded-lg bg-secondary/50">
                <div class="flex items-center gap-3">
                  <FileIcon class="h-5 w-5 text-primary" />
                  <div>
                    <p class="text-sm text-foreground truncate max-w-[200px]">{{ file.name }}</p>
                    <p class="text-xs text-muted-foreground">{{ formatFileSize(file.size) }}</p>
                    <p v-if="file.status === 'failed'" class="text-xs text-destructive mt-1 max-w-[220px]">{{ file.error }}</p>
                  </div>
                </div>
                <div class="flex items-center gap-2">
                  <RefreshCw v-if="file.status === 'encrypting'" class="h-4 w-4 animate-spin text-primary" />
                  <Check v-else-if="file.status === 'done'" class="h-4 w-4 text-primary" />
                  <button v-else class="h-8 w-8 inline-flex items-center justify-center rounded-md hover:bg-secondary" @click="removeFile(index)">
                    <X class="h-4 w-4" />
                  </button>
                </div>
              </div>
            </div>
          </div>

          <div>
            <label class="text-foreground mb-4 block text-lg font-medium">Encryption</label>
            <div class="space-y-4">
              <div class="p-3 rounded-lg bg-secondary/50 border border-border space-y-2">
                <div class="flex justify-between text-sm">
                  <span class="text-muted-foreground">File contents</span>
                  <span class="font-semibold text-primary">AES-256-GCM</span>
                </div>
                <div class="flex justify-between text-sm">
                  <span class="text-muted-foreground">File key wrapping</span>
                  <span class="font-semibold text-primary">RSA-OAEP-SHA256</span>
                </div>
                <div class="flex justify-between text-sm">
                  <span class="text-muted-foreground">Maximum size</span>
                  <span class="text-foreground">{{ formatFileSize(MAX_UPLOAD_BYTES) }}</span>
                </div>
              </div>
              <p class="text-xs text-muted-foreground">
                A fresh 256-bit key is generated per file and wrapped to your public key and to
                the recovery key. Neither key nor plaintext leaves this browser.
              </p>
              <div v-if="recoveryFingerprint" class="p-3 rounded-lg bg-secondary/50 border border-border">
                <p class="text-xs text-muted-foreground mb-1">
                  Recovery key fingerprint &mdash; verify this out of band before trusting an upload.
                </p>
                <p class="text-xs font-mono break-all text-foreground">{{ recoveryFingerprint }}</p>
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
