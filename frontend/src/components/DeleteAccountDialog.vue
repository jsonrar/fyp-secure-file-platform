<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from 'vue'
import { TriangleAlert } from 'lucide-vue-next'

import { apiErrorMessage } from '@/api/http'
import { authApi } from '@/api/auth_api'
import PasswordField from '@/components/PasswordField.vue'

const emit = defineEmits<{
  (e: 'deleted', filesDeleted: number): void
  (e: 'close'): void
}>()

const password = ref('')
const confirmation = ref('')
const errorMessage = ref('')
const isDeleting = ref(false)
const field = ref<InstanceType<typeof PasswordField> | null>(null)

/** Both, deliberately: the password proves it is them, the word proves they meant this. */
const canDelete = computed(() => password.value.length > 0 && confirmation.value === 'DELETE')

onMounted(async () => {
  await nextTick()
  field.value?.focus()
})

async function deleteAccount() {
  if (!canDelete.value) {
    errorMessage.value = 'Enter your login password and type DELETE to confirm'
    return
  }
  isDeleting.value = true
  errorMessage.value = ''
  try {
    const res = await authApi.deleteAccount({
      password: password.value,
      confirmation: 'DELETE',
    })
    password.value = ''
    emit('deleted', res.data?.data?.files_deleted ?? 0)
  } catch (error) {
    password.value = ''
    errorMessage.value = apiErrorMessage(error, 'Could not delete the account')
    await nextTick()
    field.value?.focus()
  } finally {
    isDeleting.value = false
  }
}
</script>

<template>
  <div
    class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
    @click.self="emit('close')"
  >
    <div class="w-full max-w-md rounded-xl border border-destructive/40 bg-card p-6 shadow-xl">
      <div class="flex items-center gap-2 mb-2">
        <div class="p-2 rounded-lg bg-destructive/10">
          <TriangleAlert class="h-4 w-4 text-destructive" />
        </div>
        <h2 class="text-lg font-semibold text-foreground">Delete your account</h2>
      </div>

      <p class="text-sm text-muted-foreground mb-3">
        This deletes your account and every file you have uploaded, including files you have
        shared with other people. It cannot be undone, and no one — not the team, not the
        server — can bring the files back afterwards.
      </p>

      <p class="text-sm text-muted-foreground mb-4">
        If you are here because you forgot your encryption passphrase, try
        <strong class="text-foreground">unlocking with your private key file</strong> first:
        the <code class="text-xs">.pem</code> you saved at registration opens your files
        without the passphrase. Deleting is only worth it if that file is gone too.
      </p>

      <form @submit.prevent="deleteAccount">
        <PasswordField
          ref="field"
          v-model="password"
          label="Login password"
          placeholder="Your login password"
          autocomplete="current-password"
        />

        <label class="text-sm text-foreground mt-4 mb-2 block">
          Type <code class="text-xs font-mono">DELETE</code> to confirm
        </label>
        <input
          v-model="confirmation"
          placeholder="DELETE"
          autocomplete="off"
          spellcheck="false"
          class="h-10 w-full rounded-md border border-border bg-secondary px-3 text-foreground"
        />

        <p v-if="errorMessage" class="text-sm text-destructive mt-2">{{ errorMessage }}</p>

        <div class="mt-4 flex gap-2">
          <button
            type="submit"
            class="flex-1 h-10 rounded-md bg-destructive text-white hover:bg-destructive/90 disabled:opacity-50"
            :disabled="isDeleting || !canDelete"
          >
            {{ isDeleting ? 'Deleting...' : 'Delete my account' }}
          </button>
          <button
            type="button"
            class="h-10 px-4 rounded-md border border-border hover:bg-secondary"
            @click="emit('close')"
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
  </div>
</template>
