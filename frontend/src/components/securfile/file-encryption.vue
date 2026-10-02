<script setup lang="ts">
import { AlertTriangle, Check, FileIcon, Lock, RefreshCw, Upload, X } from 'lucide-vue-next'
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { apiErrorMessage } from '@/api/http'
import { formatFileSize } from '@/api/types'
import {
  DEFAULT_ENCRYPTION_ALGORITHM,
  type EncryptionAlgorithm,
  supportedEncryptionAlgorithms,
} from '@/crypto/primitives'
import {
  classifyUploadSize,
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
const algorithm = ref<EncryptionAlgorithm>(DEFAULT_ENCRYPTION_ALGORITHM)
const algorithmChoices = ref<EncryptionAlgorithm[]>([DEFAULT_ENCRYPTION_ALGORITHM])

/**
 * Offer only what this browser can actually do.
 *
 * AES-192-GCM is specified but absent from some WebCrypto implementations, and an
 * unsupported key length fails at encryption time with an opaque error -- after the user has
 * chosen it and picked their files. Probing first keeps the menu honest.
 */
onMounted(async () => {
  try {
    algorithmChoices.value = await supportedEncryptionAlgorithms()
  } catch {
    // Leaving the default in place is right: if the probe cannot run, encryption itself
    // will fail with a message that explains far more than a broken dropdown would.
  }
})

const ALGORITHM_NOTES: Record<EncryptionAlgorithm, string> = {
  'AES-256-GCM': 'The default, and what the recovery path is tested against.',
  'AES-256-GCM-SIV':
    'AES with a synthetic IV (RFC 8452): a repeated nonce would reveal only that the same file was encrypted twice, never the key. Runs in a JavaScript library, so it is noticeably slower than the default on very large files.',
  'XChaCha20-Poly1305':
    'ChaCha20-Poly1305 with a 24-byte nonce, long enough to choose at random without ever repeating. What libsodium recommends. Fast in the browser.',
  'ChaCha20-Poly1305':
    'A different construction, not a different key length: a stream cipher authenticated by Poly1305. The usual choice on devices without AES hardware; here it runs in a JavaScript library.',
  'AES-192-GCM': 'AES at an intermediate key length. Not available in every browser.',
  'AES-128-GCM': 'AES at the shortest of its three key lengths. Still considered secure.',
}

/** A file over the limit can never upload, so the batch cannot start until it is removed. */
const hasOversizeFile = computed(() =>
  files.value.some((file) => file.status === 'pending' && classifyUploadSize(file.size) === 'too-large'),
)

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
  if (!files.value.length || hasOversizeFile.value) return
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
      await encryptAndUpload(file.raw, recipients, algorithm.value)
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
        <p class="text-muted-foreground max-w-2xl mx-auto text-pretty">Files are encrypted in your browser with the algorithm you choose below (AES-256-GCM by default). Only ciphertext is uploaded; the server never receives your readable file or its key.</p>
      </div>
      <div class="max-w-4xl mx-auto rounded-xl bg-card border border-border p-6">
        <!-- minmax(0, 1fr): a grid track otherwise never gets narrower than its widest unbreakable
             content, and the cipher dropdown's longest option pushed a phone sideways. -->
        <div class="grid grid-cols-[minmax(0,1fr)] lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)] gap-8">
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
              <div v-for="(file, index) in files" :key="`${file.name}-${index}`" class="flex items-center justify-between gap-2 p-3 rounded-lg bg-secondary/50">
                <div class="flex min-w-0 items-center gap-3">
                  <FileIcon class="h-5 w-5 shrink-0 text-primary" />
                  <div class="min-w-0">
                    <p class="text-sm text-foreground [overflow-wrap:anywhere]">{{ file.name }}</p>
                    <p class="text-xs text-muted-foreground">{{ formatFileSize(file.size) }}</p>
                    <p v-if="file.status === 'failed'" class="text-xs text-destructive mt-1">{{ file.error }}</p>
                    <p
                      v-else-if="file.status === 'pending' && classifyUploadSize(file.size) === 'too-large'"
                      class="text-xs text-destructive mt-1"
                      data-testid="upload-too-large"
                    >
                      Over the {{ formatFileSize(MAX_UPLOAD_BYTES) }} limit. Remove it to continue.
                    </p>
                    <p
                      v-else-if="file.status === 'pending' && classifyUploadSize(file.size) === 'large'"
                      class="mt-1 flex items-start gap-1 text-xs text-amber-600 dark:text-amber-400"
                      data-testid="upload-large-warning"
                    >
                      <AlertTriangle class="mt-0.5 h-3 w-3 shrink-0" />
                      <span>Large file. Encrypting needs about four times its size in memory, so it may fail on a phone or with many tabs open.</span>
                    </p>
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
                <div class="flex justify-between text-sm items-center gap-3">
                  <label for="content-algorithm" class="shrink-0 text-muted-foreground">File contents</label>
                  <!-- A select is as wide as its longest option, and "XChaCha20-Poly1305" pushed a
                       360 px phone 10 px sideways. min-w-0 lets it shrink with the row instead. -->
                  <select
                    id="content-algorithm"
                    v-model="algorithm"
                    :disabled="isEncrypting"
                    class="h-10 min-w-0 max-w-full font-semibold text-primary bg-transparent border border-border rounded-md px-2 py-1 disabled:opacity-50"
                  >
                    <option v-for="choice in algorithmChoices" :key="choice" :value="choice">
                      {{ choice }}
                    </option>
                  </select>
                </div>
                <div class="flex justify-between text-sm">
                  <span class="text-muted-foreground">File key wrapping</span>
                  <span
                    class="cursor-help font-semibold text-primary underline decoration-dotted decoration-primary/40 underline-offset-4"
                    title="RSA public-key encryption with OAEP padding. SHA-256 is the hash OAEP uses inside that padding; it is not a checksum of your file."
                  >RSA-OAEP (SHA-256)</span>
                </div>
                <div class="flex justify-between text-sm">
                  <span class="text-muted-foreground">Maximum size</span>
                  <span class="text-foreground">{{ formatFileSize(MAX_UPLOAD_BYTES) }}</span>
                </div>
              </div>
              <p class="text-xs text-muted-foreground">
                {{ ALGORITHM_NOTES[algorithm] }} A fresh key is generated per file and wrapped, with
                RSA-OAEP, to your public key and to the recovery key. (SHA-256 appears in that name
                because OAEP uses it inside its padding; it is not a checksum of your file.) Neither
                the file key nor your readable file leaves this browser unprotected.
              </p>
              <p class="text-xs text-muted-foreground">
                The choice is recorded with the file and is covered by its authentication tag, so
                each file is always read back under the algorithm it was written with. Files
                already uploaded are unaffected.
              </p>
              <div v-if="recoveryFingerprint" class="p-3 rounded-lg bg-secondary/50 border border-border">
                <p class="text-xs text-muted-foreground mb-1">
                  Recovery key fingerprint &mdash; verify this out of band before trusting an upload.
                </p>
                <p class="text-xs font-mono break-all text-foreground">{{ recoveryFingerprint }}</p>
              </div>
            </div>

            <div class="mt-8">
              <button :disabled="!files.length || isEncrypting || hasOversizeFile" class="w-full h-11 inline-flex items-center justify-center gap-2 rounded-md bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50" @click="handleEncrypt">
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
