<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { Activity, AlertCircle, CheckCircle, ChevronLeft, ChevronRight, Download, FileIcon, FileLock2, Filter, LifeBuoy, Loader2, RefreshCw, Search, Shield, Share2, Trash2 } from 'lucide-vue-next'
import { fileApi } from '@/api/file_api'
import { apiErrorCode, apiErrorMessage } from '@/api/http'
import { formatFileSize, mapFileLifecycle, mapFileStatus, unwrapData } from '@/api/types'
import type { FileSummaryOut } from '@/api/types'
import ShareDialog from '@/components/ShareDialog.vue'
import RequestRecoveryDialog from '@/components/RequestRecoveryDialog.vue'
import FileHistoryDialog from '@/components/FileHistoryDialog.vue'
import { markSharesSeen, unseenSharedIds } from '@/utils/seen-shares'
import { downloadEncryptedFile } from '@/utils/file-download'
import UnlockDialog from '@/components/UnlockDialog.vue'
import {
  downloadAndDecrypt,
  FileIntegrityError,
  FileKeyUnwrapError,
  isUnlocked,
  KeyNotUnlockedError,
  NotUnlockedError,
  onRelock,
  saveDecryptedFile,
} from '@/crypto/download'

interface EncryptedFile {
  id: string
  name: string
  originalSize: string
  encryptedSize: string
  encryptedAt: string
  status: 'verified' | 'modified' | 'pending'
  /** False when someone else owns this file and shared it with the viewer. */
  owned: boolean
  /** Who uploaded it, shown when that is not the viewer. */
  ownerName: string
  /** Set when a stale shared row is no longer authorized on the server. */
  accessError?: string
}

interface StatusConfig {
  label: string
  icon: typeof CheckCircle
  className: string
}

/** `GET /files` caps `page_size` at 100. Ask for the most the API will give per request. */
const PAGE_SIZE = 100

type FileScope = 'mine' | 'shared'

const scope = ref<FileScope>('mine')
const searchQuery = ref('')
const files = ref<EncryptedFile[]>([])
const isLoading = ref(false)
const errorMessage = ref('')
const shareFileId = ref<string | null>(null)
const recoveryFileId = ref<string | null>(null)
const historyFileId = ref<string | null>(null)
const actionMessage = ref('')
const page = ref(1)
const total = ref(0)
const downloadingId = ref<string | null>(null)
const encryptedDownloadingId = ref<string | null>(null)
const downloadBusy = computed(() => downloadingId.value !== null || encryptedDownloadingId.value !== null)
const activeDownload = computed(() => {
  const id = downloadingId.value ?? encryptedDownloadingId.value
  return id === null ? undefined : files.value.find((file) => file.id === id)
})
const downloadProgressMessage = computed(() => {
  if (!activeDownload.value) return ''
  const verb = downloadingId.value ? 'Downloading and decrypting' : 'Downloading'
  return `${verb} ${activeDownload.value.name}… Keep this page open until the download finishes.`
})
// Set while the passphrase dialog is open; holds the file to resume once unlocked.
const pendingDownloadId = ref<string | null>(null)
// The same, for a share interrupted by the unlock. Sharing needs the account key too:
// the file's key has to be unwrapped before it can be rewrapped to the recipient.
const pendingShareId = ref<string | null>(null)
const pendingShareRecipient = ref('')
const unlockKeyId = ref<string | null>(null)
const showUnlock = ref(false)

const mapFile = (file: FileSummaryOut): EncryptedFile => ({
  id: file.file_id,
  name: file.original_filename,
  originalSize: formatFileSize(file.plaintext_size),
  // AES-GCM is a stream mode, so these match; the tag is stored apart from the object.
  encryptedSize: formatFileSize(file.ciphertext_size),
  encryptedAt: new Date(file.created_at).toLocaleString(),
  // `files.status` is ACTIVE/CORRUPTED/DELETED, not the integrity vocabulary. Sending it
  // through mapFileStatus put every row on the fallback branch, so a damaged file looked
  // exactly like a healthy one.
  status: mapFileLifecycle(file.status),
  // The API has always sent this and the page has never read it, so a file someone else
  // shared with you sat in "My Encrypted Files" looking exactly like one you uploaded --
  // as though you owned and managed it, which you do not.
  owned: file.owner,
  ownerName: file.owner_username ?? 'another account',
})

const sharedIds = computed(() => files.value.filter((file) => !file.owned).map((file) => file.id))
const sharedCount = computed(() => sharedIds.value.length)
const unseenCount = ref(0)

/** Showing the shared list is what counts as having seen it. */
const showShared = () => {
  scope.value = 'shared'
  markSharesSeen(sharedIds.value)
  unseenCount.value = 0
}
const ownedCount = computed(() => files.value.filter((file) => file.owned).length)

let requestId = 0

const loadFiles = async () => {
  const thisRequest = ++requestId
  isLoading.value = true
  errorMessage.value = ''
  try {
    const res = await fileApi.listFiles({
      page: page.value,
      page_size: PAGE_SIZE,
      search: searchQuery.value.trim() || undefined,
    })
    // The API paginates: rows live under `items`. Reading anything else silently
    // yields an empty list, which reads as "no files" even when uploads succeeded.
    if (thisRequest !== requestId) return
    const data = unwrapData(res)
    files.value = data.items.map(mapFile)
    // Counted after each load, and cleared the moment the shared list is opened.
    unseenCount.value =
      scope.value === 'shared' ? 0 : unseenSharedIds(sharedIds.value).length
    if (scope.value === 'shared') markSharesSeen(sharedIds.value)
    // `total` counts every file the caller can reach, not the ones on this page. Dropping
    // it is what let the list quietly stop at one page and still call that the total.
    total.value = data.total
  } catch (error) {
    if (thisRequest !== requestId) return
    errorMessage.value = error instanceof Error ? error.message : 'Failed to load files'
  } finally {
    if (thisRequest === requestId) isLoading.value = false
  }
}

onMounted(loadFiles)

// The account key relocks itself after a spell of disuse. Nothing on screen depends on it
// directly, but a download started afterwards must ask for the passphrase again rather
// than failing, so the message says what happened before the dialog reappears.
const stopRelockListener = onRelock(() => {
  actionMessage.value = 'Your account key was locked after a period of inactivity.'
})

const pageCount = computed(() => Math.max(1, Math.ceil(total.value / PAGE_SIZE)))
const hasPreviousPage = computed(() => page.value > 1)
const hasNextPage = computed(() => page.value < pageCount.value)
const firstOnPage = computed(() => (total.value === 0 ? 0 : (page.value - 1) * PAGE_SIZE + 1))
const lastOnPage = computed(() => (page.value - 1) * PAGE_SIZE + files.value.length)

const goToPage = async (next: number) => {
  if (next < 1 || next > pageCount.value || next === page.value) return
  page.value = next
  actionMessage.value = ''
  await loadFiles()
}

/**
 * Search runs on the server, so it sees every page rather than only the fetched one.
 *
 * Debounced because it costs a request per keystroke otherwise, and the request that
 * returns last is not necessarily the one for the current text -- `requestId` drops any
 * response that a newer search has already superseded.
 */
const SEARCH_DEBOUNCE_MS = 250
let searchTimer: ReturnType<typeof setTimeout> | undefined

watch(searchQuery, () => {
  if (searchTimer !== undefined) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    // A narrower result set rarely has the page the user was on; start from the first.
    page.value = 1
    void loadFiles()
  }, SEARCH_DEBOUNCE_MS)
})

onBeforeUnmount(() => {
  if (searchTimer !== undefined) clearTimeout(searchTimer)
  stopRelockListener()
})

// The server has already applied the text search; the split by ownership is local, because
// `GET /files` returns both in one list and only marks which is which.
const filteredFiles = computed(() =>
  files.value.filter((file) => (scope.value === 'mine' ? file.owned : !file.owned)),
)

const revokedAccessMessage =
  'This shared file is no longer available. Its owner may have revoked access or deleted it. Contact the person who shared it with you.'

const markSharedFileUnavailable = (id: string, error: unknown): boolean => {
  const row = files.value.find((file) => file.id === id)
  if (row && !row.owned && apiErrorCode(error) === 'file_not_found') {
    row.accessError = revokedAccessMessage
    errorMessage.value = revokedAccessMessage
    return true
  }
  return false
}

const handleDelete = async (id: string) => {
  actionMessage.value = ''
  try {
    await fileApi.delete(id)
    files.value = files.value.filter((f) => f.id !== id)
    total.value = Math.max(0, total.value - 1)
    // Removing the last row of the last page would otherwise strand the view on a page
    // that no longer exists, showing an empty table over a non-zero total.
    if (!files.value.length && page.value > 1) {
      await goToPage(page.value - 1)
    }
    actionMessage.value = 'File deleted'
  } catch (error) {
    actionMessage.value = error instanceof Error ? error.message : 'Delete failed'
  }
}

/**
 * Download, decrypt in the page, and hand the plaintext to the browser.
 *
 * The account key has to be open first, so a locked session raises the passphrase dialog
 * and remembers which file to resume. Nothing is written to disk until the AES-GCM tag has
 * authenticated: a file that fails to decrypt is never saved half-formed.
 */
const handleDownload = async (id: string) => {
  if (downloadBusy.value) return
  actionMessage.value = ''
  errorMessage.value = ''
  const row = files.value.find((file) => file.id === id)
  if (row?.accessError) return
  if (!isUnlocked()) {
    try {
      // A stale recipient tab can still show a row after its owner revokes access. Check
      // before asking for a passphrase, otherwise the user unlocks successfully and then
      // sees an apparently dead download button.
      await fileApi.getFile(id)
      pendingDownloadId.value = id
      unlockKeyId.value = null
      showUnlock.value = true
    } catch (error) {
      if (!markSharedFileUnavailable(id, error)) {
        errorMessage.value = apiErrorMessage(error, 'Could not check access to this file')
      }
    }
    return
  }

  downloadingId.value = id
  try {
    const file = await downloadAndDecrypt(id)
    saveDecryptedFile(file)
    actionMessage.value = `Decrypted and saved ${file.filename}`
  } catch (error) {
    if (error instanceof KeyNotUnlockedError) {
      // Ordinary after a key rotation: the file is wrapped to an older account key.
      pendingDownloadId.value = id
      unlockKeyId.value = error.keyId
      showUnlock.value = true
      return
    }
    if (error instanceof NotUnlockedError) {
      pendingDownloadId.value = id
      unlockKeyId.value = null
      showUnlock.value = true
      return
    }
    if (error instanceof FileIntegrityError) {
      // An integrity finding, not a transport or permission problem. Mark the row so the
      // state persists after the message is replaced by the next action.
      const row = files.value.find((f) => f.id === id)
      if (row) row.status = 'modified'
      errorMessage.value = error.message
      return
    }
    if (error instanceof FileKeyUnwrapError) {
      errorMessage.value = error.message
      return
    }
    if (!markSharedFileUnavailable(id, error)) {
      errorMessage.value = apiErrorMessage(error, 'Download failed')
    }
  } finally {
    downloadingId.value = null
  }
}

const handleEncryptedDownload = async (file: EncryptedFile) => {
  if (downloadBusy.value) return
  actionMessage.value = ''
  errorMessage.value = ''
  encryptedDownloadingId.value = file.id
  try {
    await downloadEncryptedFile(file.id, file.name)
    actionMessage.value = `Encrypted download started for ${file.name}. The file remains encrypted.`
  } catch (error) {
    if (!markSharedFileUnavailable(file.id, error)) {
      errorMessage.value = apiErrorMessage(error, 'Encrypted download failed')
    }
  } finally {
    encryptedDownloadingId.value = null
  }
}

const onUnlocked = async () => {
  showUnlock.value = false
  unlockKeyId.value = null
  const resumeDownload = pendingDownloadId.value
  const resumeShare = pendingShareId.value
  pendingDownloadId.value = null
  pendingShareId.value = null
  if (resumeDownload) {
    await handleDownload(resumeDownload)
  } else if (resumeShare) {
    shareFileId.value = resumeShare
  }
}

const closeUnlock = () => {
  showUnlock.value = false
  unlockKeyId.value = null
  pendingDownloadId.value = null
  pendingShareId.value = null
  pendingShareRecipient.value = ''
}

const handleIntegrityCheck = async (id: string) => {
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

const openShare = (id: string) => {
  if (!isUnlocked()) {
    pendingShareId.value = id
    pendingShareRecipient.value = ''
    unlockKeyId.value = null
    showUnlock.value = true
    return
  }
  shareFileId.value = id
}

const historyFile = computed(() => files.value.find((file) => file.id === historyFileId.value))
const recoveryFile = computed(() => files.value.find((file) => file.id === recoveryFileId.value))

const closeShare = () => {
  shareFileId.value = null
  pendingShareRecipient.value = ''
}

const onRecoveryRequested = () => {
  actionMessage.value = 'Recovery request submitted. Track it under Operations (/admin).'
}

const onShared = (username: string) => {
  // The dialog stays open: it now lists who holds the file, and seeing the new name appear
  // is the confirmation. Closing it would hide the thing that just changed.
  actionMessage.value = `Shared with ${username}`
}

const onRevoked = (username: string) => {
  actionMessage.value = `Revoked ${username}'s access`
}

/** The rewrap needs the account key open; stand the share down and raise the passphrase. */
const onShareNeedsUnlock = (keyId: string | null, recipient: string) => {
  pendingShareId.value = shareFileId.value
  pendingShareRecipient.value = recipient
  shareFileId.value = null
  unlockKeyId.value = keyId
  showUnlock.value = true
}

const shareFilename = computed(
  () => files.value.find((file) => file.id === shareFileId.value)?.name,
)

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
            <div class="inline-flex rounded-lg border border-border p-1 mb-2">
              <button
                type="button"
                class="h-8 px-3 rounded-md text-sm transition-colors"
                :class="scope === 'mine' ? 'bg-secondary text-foreground font-medium' : 'text-muted-foreground hover:text-foreground'"
                @click="scope = 'mine'"
              >
                My Files ({{ ownedCount }})
              </button>
              <button
                type="button"
                class="h-8 px-3 rounded-md text-sm transition-colors"
                :class="scope === 'shared' ? 'bg-secondary text-foreground font-medium' : 'text-muted-foreground hover:text-foreground'"
                @click="showShared"
              >
                Shared with me ({{ sharedCount }})
                <span
                  v-if="unseenCount > 0"
                  class="ml-1 inline-flex items-center justify-center min-w-5 h-5 px-1 rounded-full bg-primary text-primary-foreground text-xs"
                >{{ unseenCount }}</span>
              </button>
            </div>
            <p class="text-muted-foreground text-sm">
              <template v-if="searchQuery.trim()">{{ total }} {{ total === 1 ? 'match' : 'matches' }} for "{{ searchQuery.trim() }}"</template>
              <template v-else>Total {{ total }} encrypted {{ total === 1 ? 'file' : 'files' }}</template><span v-if="total > files.length">, showing {{ firstOnPage }}-{{ lastOnPage }}</span>
            </p>
          </div>
          <div class="flex items-center gap-2">
            <div class="relative">
              <Search class="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <input v-model="searchQuery" placeholder="Search your files..." class="h-10 w-full md:w-64 rounded-md border border-border bg-secondary pl-9 pr-3" />
            </div>
            <button class="h-10 w-10 inline-flex items-center justify-center rounded-md border border-border hover:bg-secondary" @click="loadFiles">
              <RefreshCw class="h-4 w-4" :class="{ 'animate-spin': isLoading }" />
            </button>
            <button class="h-10 w-10 inline-flex items-center justify-center rounded-md border border-border hover:bg-secondary"><Filter class="h-4 w-4" /></button>
          </div>
        </div>

        <p v-if="errorMessage" class="text-sm text-destructive mb-4">{{ errorMessage }}</p>
        <p v-if="actionMessage" class="text-sm text-primary mb-4">{{ actionMessage }}</p>
        <div
          v-if="downloadProgressMessage"
          class="mb-4 flex items-center gap-2 rounded-md border border-border bg-secondary px-3 py-2 text-sm font-medium text-foreground"
          role="status"
          aria-live="polite"
        >
          <Loader2 class="h-4 w-4 shrink-0 animate-spin" />
          <span>{{ downloadProgressMessage }}</span>
        </div>
        <p class="text-sm text-muted-foreground mb-4">
          Download encrypted saves a .ciphertext file without your passphrase. Use Download and decrypt to save the original file.
        </p>

        <div v-if="isLoading && !files.length" class="text-center py-12 text-muted-foreground">
          Loading files...
        </div>

        <div v-else-if="!filteredFiles.length" class="text-center py-12 text-muted-foreground">
          <template v-if="searchQuery.trim()">No file matches "{{ searchQuery.trim() }}".</template>
          <template v-else-if="scope === 'shared'">No one has shared a file with you yet.</template>
          <template v-else>No encrypted files yet. Upload your first file to get started.</template>
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
                      <p v-if="!file.owned" class="text-xs text-muted-foreground">Shared by {{ file.ownerName }}</p>
                      <p v-if="file.accessError" class="mt-1 text-xs text-destructive">{{ file.accessError }}</p>
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
                  <div class="inline-flex flex-wrap justify-end gap-1">
                    <button
                      class="h-8 w-8 inline-flex items-center justify-center rounded-md hover:bg-secondary disabled:opacity-40"
                      :title="downloadingId === file.id ? 'Decrypting...' : 'Download and decrypt'"
                      aria-label="Download and decrypt"
                      :disabled="downloadBusy || Boolean(file.accessError)"
                      @click="handleDownload(file.id)"
                    >
                      <Loader2 v-if="downloadingId === file.id" class="h-4 w-4 animate-spin" />
                      <Download v-else class="h-4 w-4" />
                    </button>
                    <button
                      type="button"
                      class="h-8 w-8 inline-flex items-center justify-center rounded-md hover:bg-secondary disabled:opacity-40"
                      title="Download encrypted file"
                      aria-label="Download encrypted file"
                      :disabled="downloadBusy || Boolean(file.accessError)"
                      @click="handleEncryptedDownload(file)"
                    >
                      <Loader2 v-if="encryptedDownloadingId === file.id" class="h-4 w-4 shrink-0 animate-spin" />
                      <FileLock2 v-else class="h-4 w-4 shrink-0" />
                    </button>
                    <!-- Sharing and deleting belong to the owner. A recipient's grant carries
                         can_share=false and can_manage=false, so these would only ever return
                         a 404 -- showing them promises something the server will refuse. -->
                    <button
                      type="button"
                      class="h-8 w-8 inline-flex items-center justify-center rounded-md hover:bg-secondary disabled:opacity-40"
                      title="Request recovery"
                      aria-label="Request recovery"
                      :disabled="Boolean(file.accessError)"
                      @click="recoveryFileId = file.id"
                    >
                      <LifeBuoy class="h-4 w-4" />
                    </button>
                    <button
                      class="h-8 w-8 inline-flex items-center justify-center rounded-md hover:bg-secondary"
                      title="Access history"
                      @click="historyFileId = file.id"
                    >
                      <Activity class="h-4 w-4" />
                    </button>
                    <button v-if="file.owned" class="h-8 w-8 inline-flex items-center justify-center rounded-md hover:bg-secondary" title="Share" @click="openShare(file.id)">
                      <Share2 class="h-4 w-4" />
                    </button>
                    <button v-if="file.owned" class="h-8 w-8 inline-flex items-center justify-center rounded-md hover:bg-secondary text-destructive" title="Delete" @click="handleDelete(file.id)">
                      <Trash2 class="h-4 w-4" />
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div v-if="pageCount > 1" class="flex items-center justify-between gap-4 mt-6 pt-4 border-t border-border">
          <p class="text-muted-foreground text-sm">Page {{ page }} of {{ pageCount }}</p>
          <div class="flex items-center gap-2">
            <button
              class="h-9 px-3 inline-flex items-center gap-1 rounded-md border border-border hover:bg-secondary disabled:opacity-40 disabled:cursor-not-allowed"
              :disabled="!hasPreviousPage || isLoading"
              @click="goToPage(page - 1)"
            >
              <ChevronLeft class="h-4 w-4" />
              Previous
            </button>
            <button
              class="h-9 px-3 inline-flex items-center gap-1 rounded-md border border-border hover:bg-secondary disabled:opacity-40 disabled:cursor-not-allowed"
              :disabled="!hasNextPage || isLoading"
              @click="goToPage(page + 1)"
            >
              Next
              <ChevronRight class="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>
    </div>

    <FileHistoryDialog
      v-if="historyFile"
      :file-id="historyFile.id"
      :filename="historyFile.name"
      :owned="historyFile.owned"
      @close="historyFileId = null"
    />
    <ShareDialog
      v-if="shareFileId !== null"
      :file-id="shareFileId"
      :filename="shareFilename"
      :initial-recipient="pendingShareRecipient"
      @close="closeShare"
      @shared="onShared"
      @revoked="onRevoked"
      @needs-unlock="onShareNeedsUnlock"
    />
    <RequestRecoveryDialog
      v-if="recoveryFile"
      :file-id="recoveryFile.id"
      :filename="recoveryFile.name"
      @close="recoveryFileId = null"
      @requested="onRecoveryRequested"
    />
    <UnlockDialog
      v-if="showUnlock"
      :key-id="unlockKeyId"
      @unlocked="onUnlocked"
      @close="closeUnlock"
    />
  </section>
</template>
