<script setup lang="ts">
import { ChevronRight, FileIcon, LifeBuoy, Shield, Upload } from 'lucide-vue-next'
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { fileApi } from '@/api/file_api'
import { formatFileSize, unwrapData, type FileSummaryOut } from '@/api/types'
import DeleteAccountDialog from '@/components/DeleteAccountDialog.vue'
import { useAuthStore } from '@/stores/auth_store'

const router = useRouter()
const auth = useAuthStore()
const showDelete = ref(false)

const recent = ref<FileSummaryOut[]>([])
const total = ref<number | null>(null)
const isLoading = ref(true)

/**
 * The count and the recent rows are a hint, not a gate. Every destination below is a
 * plain link, so a failed or slow call must leave them usable rather than blocking the
 * page -- this is the screen a signed-in user lands on, and it cannot be the thing that
 * strands them.
 */
onMounted(async () => {
  try {
    await auth.loadUser()
    const data = unwrapData(await fileApi.listFiles({ page: 1, page_size: 5 }))
    recent.value = data.items
    total.value = data.total
  } catch {
    total.value = null
  } finally {
    isLoading.value = false
  }
})

/**
 * The account is gone server-side; clear the local session so the app does not keep
 * rendering a signed-in shell against a user that no longer exists, and offer the only
 * thing left to do -- register again.
 */
const onDeleted = () => {
  showDelete.value = false
  // Account deletion already revoked every session server-side.
  auth.clearLocalSession()
  router.push({ path: '/register', query: { deleted: '1' } })
}

const destinations = computed(() => {
  const items = [
    {
      to: '/upload',
      icon: Upload,
      title: 'Upload & Encrypt',
      body: 'Encrypt a new file in your browser with AES-256-GCM. Only the ciphertext is uploaded.',
      cta: 'Encrypt a file',
    },
    {
      to: '/files',
      icon: FileIcon,
      title: 'My Files',
      body: 'Download and decrypt, share with another account, verify integrity, or delete what you have already uploaded.',
      cta: 'Manage files',
    },
    {
      to: '/audit-logs',
      icon: Shield,
      title: 'Access Records',
      body: 'Review the tamper-evident audit log of every upload, download, and share on your account.',
      cta: 'View records',
    },
    {
      to: '/admin',
      icon: LifeBuoy,
      title: auth.isAdmin ? 'Admin console' : auth.isRecoveryReviewer ? 'Recovery review' : 'Recovery requests',
      body: auth.isRecoveryReviewer
        ? 'Review recovery requests, manage users and files, verify the audit hash chain, and register the recovery public key.'
        : 'Track your recovery requests, or cancel one that is no longer needed.',
      cta: auth.isRecoveryReviewer ? 'Open console' : 'View requests',
    },
  ]
  return items
})
</script>

<template>
  <section id="workspace" class="py-20">
    <div class="container mx-auto px-4">
      <div class="text-center mb-16">
        <h2 class="text-3xl md:text-4xl font-bold text-foreground mb-4">Your Workspace</h2>
        <p class="text-muted-foreground max-w-2xl mx-auto text-pretty">
          Pick up where you left off. Encrypt something new, or manage and share the files you
          have already uploaded.
        </p>
      </div>

      <div class="grid gap-6 max-w-5xl mx-auto sm:grid-cols-2 lg:grid-cols-4">
        <RouterLink
          v-for="item in destinations"
          :key="item.to"
          :to="item.to"
          class="group flex flex-col rounded-xl bg-card border border-border p-6 hover:border-primary/50 hover:shadow-lg transition-all"
        >
          <div class="p-2 rounded-lg bg-primary/10 w-fit mb-4">
            <component :is="item.icon" class="h-6 w-6 text-primary" />
          </div>
          <h3 class="text-lg font-medium text-foreground mb-2">{{ item.title }}</h3>
          <p class="text-sm text-muted-foreground text-pretty flex-1">{{ item.body }}</p>
          <span class="mt-4 inline-flex items-center gap-1 text-sm font-medium text-primary">
            {{ item.cta }}
            <ChevronRight class="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
          </span>
        </RouterLink>
      </div>

      <div v-if="!isLoading && total !== null" class="max-w-5xl mx-auto mt-12">
        <div class="rounded-xl bg-card border border-border p-6">
          <div class="flex items-center justify-between gap-4 mb-4">
            <h3 class="text-lg font-medium text-foreground">
              Recent files
              <span class="text-muted-foreground font-normal text-sm">({{ total }} total)</span>
            </h3>
            <RouterLink
              v-if="total > 0"
              to="/files"
              class="inline-flex min-h-10 items-center gap-1 text-sm font-medium text-primary hover:underline"
            >
              See all
              <ChevronRight class="h-4 w-4" />
            </RouterLink>
          </div>

          <p v-if="!recent.length" class="text-sm text-muted-foreground">
            Nothing uploaded yet. Encrypt your first file to get started.
          </p>

          <ul v-else class="divide-y divide-border">
            <li v-for="file in recent" :key="file.file_id" class="flex items-center gap-3 py-3">
              <FileIcon class="h-4 w-4 text-primary shrink-0" />
              <span class="text-sm text-foreground truncate flex-1">{{ file.original_filename }}</span>
              <span class="text-xs text-muted-foreground shrink-0">{{ formatFileSize(file.plaintext_size) }}</span>
            </li>
          </ul>
        </div>
      </div>

      <div class="max-w-5xl mx-auto mt-12">
        <details class="rounded-xl border border-border bg-card/50 p-4">
          <summary class="text-sm text-muted-foreground cursor-pointer select-none">
            Account options
          </summary>
          <div class="mt-4 pt-4 border-t border-border">
            <p class="text-sm text-foreground mb-1">Delete this account</p>
            <p class="text-xs text-muted-foreground mb-3 max-w-2xl text-pretty">
              Removes the account and every file uploaded from it. There is no way to reverse
              this and no way to recover the files afterwards. If you are locked out by a
              forgotten passphrase, unlocking with your saved private key file is the thing to
              try first — deleting is the last resort, not the first.
            </p>
            <button
              type="button"
              class="h-9 px-4 rounded-md border border-destructive/50 text-destructive hover:bg-destructive/10 transition-colors text-sm"
              @click="showDelete = true"
            >
              Delete account
            </button>
          </div>
        </details>
      </div>
    </div>

    <DeleteAccountDialog
      v-if="showDelete"
      @deleted="onDeleted"
      @close="showDelete = false"
    />
  </section>
</template>
